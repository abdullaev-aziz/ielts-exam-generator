"""QA Worker — subscribes to ``ielts.stage.qa``, runs Agent 4 (validation).

Publishes final validation event (done=True) to ``ielts.result.{job_id}``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from common.log_config import setup_logging
from workers.common import ProgressCallback, run_worker
from nats.js import JetStreamContext

from listening.agents.part1.main_agent import run_qa_stage
from listening.agents.part1.agent2 import IELTSQuestionSet
from listening.agents.part1.agent3 import IELTSTTSScript


async def handle(
    payload: dict[str, Any],
    js: JetStreamContext,
    on_progress: ProgressCallback,
) -> None:
    question_set = IELTSQuestionSet.model_validate(payload["question_set"])
    tts_script = IELTSTTSScript.model_validate(payload["tts_script"])
    cdn_url: str = payload["cdn_url"]
    await run_qa_stage(question_set, tts_script, cdn_url, on_progress=on_progress)


def main() -> None:
    import asyncio

    setup_logging()
    asyncio.run(
        run_worker(
            worker_name="qa-worker",
            subscribe_subject="ielts.stage.qa",
            handler=handle,
            ack_wait=300,  # 5 min — Agent 4 (2 min) + retries
        )
    )


if __name__ == "__main__":
    main()
