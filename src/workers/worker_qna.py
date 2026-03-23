"""Q&A Worker — subscribes to ``ielts.stage.qna``, runs Agent 1 + Agent 2.

Publishes results to ``ielts.stage.tts`` and progress to ``ielts.result.{job_id}``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from common.log_config import setup_logging
from workers.common import ProgressCallback, run_worker
from nats.js import JetStreamContext

from listening.agents.part1.main_agent import run_qna_stage

NEXT_SUBJECT = "ielts.stage.tts"


async def handle(
    payload: dict[str, Any],
    js: JetStreamContext,
    on_progress: ProgressCallback,
) -> None:
    blueprint, question_set = await run_qna_stage(on_progress=on_progress)
    await js.publish(
        NEXT_SUBJECT,
        json.dumps({
            "job_id": payload["job_id"],
            "blueprint": blueprint.model_dump(),
            "question_set": question_set.model_dump(),
        }).encode(),
    )


def main() -> None:
    import asyncio

    setup_logging()
    asyncio.run(
        run_worker(
            worker_name="qna-worker",
            subscribe_subject="ielts.stage.qna",
            handler=handle,
            ack_wait=600,  # 10 min — Agent 1 (3 min) + Agent 2 (4 min) + retries
        )
    )


if __name__ == "__main__":
    main()
