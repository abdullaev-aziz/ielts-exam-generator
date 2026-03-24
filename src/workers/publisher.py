"""IELTS NATS client — sends a generation request and streams progress events.

Usage:
  python nats_publisher.py              # resume last job from NATS, or start a new one
  python nats_publisher.py <job_id>     # resume a specific job (replays all events)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

import nats
import nats.js.api as js_api
from nats.aio.msg import Msg
from nats.js import JetStreamContext

from common.log_config import setup_logging
import os

from workers.common import RESULTS_STREAM

logger = logging.getLogger("ielts.publisher")


def _print_event(data: dict[str, Any]) -> None:
    type_ = data.get("type")
    if type_ == "status":
        logger.info("[status] %s", data.get("data", {}).get("message"))
    elif type_ == "questions":
        logger.info("[questions] Questions and answers received")
        print(json.dumps(data.get("data", {}), indent=2))
    elif type_ == "audio":
        logger.info("[audio] Audio ready: %s", data.get("data", {}).get("cdn_url"))
    elif type_ == "validation":
        logger.info("[validation] QA result: %s", data.get("data", {}).get("result"))
    elif type_ == "error":
        logger.error("[error] Pipeline failed: %s", data.get("error"))


async def _find_incomplete_job_id(js: JetStreamContext) -> str | None:
    """Get the most recent in-progress job_id from the IELTS_RESULTS stream.

    Returns None if the last job already finished (has "done": true) or if
    no jobs exist.
    """
    try:
        msg = await js.get_msg(RESULTS_STREAM, last_by_subj="ielts.result.*")
        data = json.loads(msg.data)
        if data.get("done"):
            return None
        return msg.subject.split(".")[-1]
    except Exception:
        return None


async def _async_main() -> None:
    setup_logging()

    job_id: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    nc = await nats.connect(os.environ["NATS_URL"])
    js = nc.jetstream()

    if not job_id:
        job_id = await _find_incomplete_job_id(js)
        if job_id:
            logger.info("Resuming last job from NATS: %s", job_id)

    if not job_id:
        resp = await nc.request("ielts.generate", b"{}", timeout=5)
        job_id = json.loads(resp.data)["job_id"]
        logger.info("Job started: %s", job_id)
    elif len(sys.argv) > 1:
        logger.info("Resuming job: %s", job_id)

    done_event = asyncio.Event()

    async def on_msg(msg: Msg) -> None:
        data: dict[str, Any] = json.loads(msg.data)
        _print_event(data)
        if data.get("done"):
            done_event.set()

    sub = await js.subscribe(
        f"ielts.result.{job_id}",
        cb=on_msg,
        ordered_consumer=True,
        config=js_api.ConsumerConfig(
            deliver_policy=js_api.DeliverPolicy.ALL,
        ),
    )

    await done_event.wait()
    await sub.unsubscribe()
    await nc.close()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
