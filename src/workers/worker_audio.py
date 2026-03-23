"""Audio Worker — subscribes to ``ielts.stage.audio``, runs Qwen3-TTS + S3 upload.

Publishes results to ``ielts.stage.qa`` and progress to ``ielts.result.{job_id}``.
Requires GPU and S3 credentials.
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

from listening.agents.part1.main_agent import run_audio_stage
from listening.agents.part1.agent3 import IELTSTTSScript

NEXT_SUBJECT = "ielts.stage.qa"


async def handle(
    payload: dict[str, Any],
    js: JetStreamContext,
    on_progress: ProgressCallback,
) -> None:
    tts_script = IELTSTTSScript.model_validate(payload["tts_script"])
    cdn_url = await run_audio_stage(tts_script, on_progress=on_progress)
    await js.publish(
        NEXT_SUBJECT,
        json.dumps({
            "job_id": payload["job_id"],
            "question_set": payload["question_set"],
            "tts_script": payload["tts_script"],
            "cdn_url": cdn_url,
        }).encode(),
    )


def main() -> None:
    import asyncio

    setup_logging()
    asyncio.run(
        run_worker(
            worker_name="audio-worker",
            subscribe_subject="ielts.stage.audio",
            handler=handle,
            ack_wait=3600,  # 1 hour — GPU audio generation can take up to 60 min
        )
    )


if __name__ == "__main__":
    main()
