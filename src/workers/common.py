"""Shared NATS JetStream infrastructure for all workers and the dispatcher.

Centralises stream definitions, connection setup, and the worker loop pattern
so that individual worker files only need to define their processing logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import traceback
from typing import Any, Callable, Awaitable

import os

import nats
import nats.js.api as js_api
from dotenv import load_dotenv
from nats.aio.client import Client as NatsClient
from nats.js import JetStreamContext

load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, ".env"))

logger = logging.getLogger("ielts.nats")

# ── Stream definitions ───────────────────────────────────────────────────────

RESULTS_STREAM = "IELTS_RESULTS"
RESULTS_SUBJECTS = ["ielts.result.*"]
STAGES_STREAM = "IELTS_STAGES"
STAGES_SUBJECTS = ["ielts.stage.*"]
STREAM_MAX_AGE = 2 * 60 * 60  # 2 hours in seconds



async def ensure_streams(js: JetStreamContext) -> None:
    """Create the IELTS_STAGES and IELTS_RESULTS streams (idempotent)."""
    for name, subjects in [
        (RESULTS_STREAM, RESULTS_SUBJECTS),
        (STAGES_STREAM, STAGES_SUBJECTS),
    ]:
        config = js_api.StreamConfig(name=name, subjects=subjects, max_age=STREAM_MAX_AGE)
        try:
            await js.add_stream(config)
            logger.info("Stream '%s' created.", name)
        except Exception as exc:
            if "already in use" in str(exc).lower():
                logger.info("Stream '%s' already exists.", name)
            else:
                raise


# ── Progress callback factory ────────────────────────────────────────────────

ProgressCallback = Callable[[str, dict[str, Any], bool], Awaitable[None]]


def make_progress_callback(
    js: JetStreamContext, job_id: str
) -> ProgressCallback:
    """Return an ``on_progress(type_, data, done=False)`` coroutine bound to *job_id*."""

    async def publish(type_: str, data: dict[str, Any], done: bool = False) -> None:
        event: dict[str, Any] = {"type": type_, "job_id": job_id, "data": data}
        if done:
            event["done"] = True
        await js.publish(f"ielts.result.{job_id}", json.dumps(event).encode())

    return publish


# ── Generic worker loop ──────────────────────────────────────────────────────

WorkerHandler = Callable[
    [dict[str, Any], JetStreamContext, ProgressCallback],
    Awaitable[None],
]


async def run_worker(
    *,
    worker_name: str,
    subscribe_subject: str,
    handler: WorkerHandler,
    ack_wait: int | None = None,
) -> None:
    """Connect to NATS and run a pull-subscribe worker loop until SIGINT/SIGTERM.

    Parameters
    ----------
    worker_name:
        Durable consumer name (e.g. ``"qna-worker"``).
    subscribe_subject:
        JetStream subject to pull from (e.g. ``"ielts.stage.qna"``).
    handler:
        Async callable ``(payload, js, on_progress) -> None``.
        Responsible for processing the job and publishing results to the next
        stage subject.  On success the message is ACKed automatically.
    ack_wait:
        Consumer ``ack_wait`` in seconds.  Defaults to ``None`` (NATS default
        of 30 s). Set to a large value for long-running stages like audio.
    """
    nc: NatsClient = await nats.connect(os.environ["NATS_URL"])
    js = nc.jetstream()
    await ensure_streams(js)

    consumer_cfg = js_api.ConsumerConfig(ack_wait=ack_wait) if ack_wait else None

    # Delete stale consumer if its config doesn't match (e.g. ack_wait changed).
    if consumer_cfg:
        try:
            info = await js.consumer_info(STAGES_STREAM, worker_name)
            if info.config.ack_wait != ack_wait:  # nats-py uses seconds
                logger.info("[%s] Consumer config changed — recreating.", worker_name)
                await js.delete_consumer(STAGES_STREAM, worker_name)
        except Exception:
            pass  # Consumer doesn't exist yet — will be created below.

    psub = await js.pull_subscribe(
        subscribe_subject, worker_name, config=consumer_cfg
    )
    logger.info("[%s] Listening on '%s'…", worker_name, subscribe_subject)

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    while not stop.is_set():
        try:
            msgs = await psub.fetch(1, timeout=5)
        except asyncio.TimeoutError:
            continue
        except Exception as exc:
            if stop.is_set():
                break
            logger.warning("[%s] fetch error: %s", worker_name, exc)
            await asyncio.sleep(1)
            continue

        for msg in msgs:
            payload: dict[str, Any] = json.loads(msg.data)
            job_id: str = payload["job_id"]
            logger.info("[%s] Processing job %s", worker_name, job_id)

            on_progress = make_progress_callback(js, job_id)
            try:
                await handler(payload, js, on_progress)
                await msg.ack()
                logger.info("[%s] Job %s done.", worker_name, job_id)
            except Exception:
                tb = traceback.format_exc()
                logger.error("[%s] Job %s ERROR:\n%s", worker_name, job_id, tb)
                await js.publish(
                    f"ielts.result.{job_id}",
                    json.dumps({
                        "type": "error",
                        "job_id": job_id,
                        "error": tb,
                        "done": True,
                    }).encode(),
                )
                await msg.ack()

    await nc.drain()
    await nc.close()
    logger.info("[%s] Stopped.", worker_name)
