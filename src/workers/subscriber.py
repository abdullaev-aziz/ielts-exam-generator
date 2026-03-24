"""IELTS Dispatcher — receives requests on ``ielts.generate`` and dispatches jobs.

No agents run here; it only assigns a job_id and publishes to ``ielts.stage.qna``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import uuid

import nats
from nats.aio.msg import Msg

from common.log_config import setup_logging
import os

from workers.common import ensure_streams

logger = logging.getLogger("ielts.dispatcher")


async def _async_main() -> None:
    setup_logging()

    nc = await nats.connect(os.environ["NATS_URL"])
    js = nc.jetstream()
    await ensure_streams(js)

    async def handle_request(msg: Msg) -> None:
        job_id = str(uuid.uuid4())
        await msg.respond(json.dumps({"job_id": job_id}).encode())
        await js.publish("ielts.stage.qna", json.dumps({"job_id": job_id}).encode())
        logger.info("Job %s dispatched → ielts.stage.qna", job_id)

    await nc.subscribe("ielts.generate", cb=handle_request)
    logger.info("Listening on 'ielts.generate'… (Ctrl+C to stop)")

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    await nc.drain()
    await nc.close()
    logger.info("Dispatcher stopped.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
