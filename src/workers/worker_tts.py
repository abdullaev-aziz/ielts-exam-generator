"""TTS Script Worker — subscribes to ``ielts.stage.tts``, runs Agent 3.

Publishes results to ``ielts.stage.audio`` and progress to ``ielts.result.{job_id}``.
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

from listening.agents.part1.main_agent import run_tts_stage
from listening.agents.part1.agent1 import IELTSBlueprint
from listening.agents.part1.agent2 import IELTSQuestionSet

NEXT_SUBJECT = "ielts.stage.audio"


async def handle(
    payload: dict[str, Any],
    js: JetStreamContext,
    on_progress: ProgressCallback,
) -> None:
    blueprint = IELTSBlueprint.model_validate(payload["blueprint"])
    question_set = IELTSQuestionSet.model_validate(payload["question_set"])
    tts_script = await run_tts_stage(blueprint, question_set, on_progress=on_progress)
    await js.publish(
        NEXT_SUBJECT,
        json.dumps({
            "job_id": payload["job_id"],
            "question_set": payload["question_set"],
            "tts_script": tts_script.model_dump(),
        }).encode(),
    )


def main() -> None:
    import asyncio

    setup_logging()
    asyncio.run(
        run_worker(
            worker_name="tts-worker",
            subscribe_subject="ielts.stage.tts",
            handler=handle,
            ack_wait=300,  # 5 min — Agent 3 (3 min) + retries
        )
    )


if __name__ == "__main__":
    main()
