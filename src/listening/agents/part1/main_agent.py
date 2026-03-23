"""Pipeline orchestrator — runs the 4-stage IELTS generation pipeline.

Exposes individual stage functions (``run_qna_stage``, ``run_tts_stage``,
``run_audio_stage``, ``run_qa_stage``) and a convenience ``run_pipeline`` wrapper.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Awaitable

from agents import Runner

from listening.agents.part1.agent1 import skeleton_agent, IELTSBlueprint
from listening.agents.part1.agent2 import question_agent, IELTSQuestionSet
from listening.agents.part1.agent3 import tts_agent, IELTSTTSScript
from listening.agents.part1.agent4 import qa_agent

from audio.generator import generate_and_upload_to_s3

logger = logging.getLogger("ielts.pipeline")

# Type alias for the on_progress callback used by all stage functions.
ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None]] | None

# Per-step timeout in seconds.
AGENT_TIMEOUTS: dict[str, int] = {
    "agent1": 3 * 60,
    "agent2": 4 * 60,
    "agent3": 3 * 60,
    "audio":  90 * 60,
    "agent4": 2 * 60,
}
MAX_RETRIES = 2


async def _run_with_retry(
    coro_factory: Callable[[], Awaitable[Any]],
    name: str,
    on_progress: ProgressCallback = None,
) -> Any:
    """Run a coroutine with timeout, retrying up to MAX_RETRIES on TimeoutError."""
    timeout = AGENT_TIMEOUTS[name]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(coro_factory(), timeout=timeout)
        except asyncio.TimeoutError:
            msg = f"{name} timed out after {timeout}s (attempt {attempt}/{MAX_RETRIES})"
            logger.warning(msg)
            if on_progress:
                await on_progress("status", {"message": msg})
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"{name} failed: timed out after {MAX_RETRIES} attempts")


async def run_qna_stage(
    on_progress: ProgressCallback = None,
) -> tuple[IELTSBlueprint, IELTSQuestionSet]:
    """Run Agent 1 (blueprint) + Agent 2 (questions & answers)."""

    async def status(msg: str) -> None:
        if on_progress:
            await on_progress("status", {"message": msg})

    await status("Running Agent 1 (blueprint)...")
    r1 = await _run_with_retry(
        lambda: Runner.run(skeleton_agent, "Create IELTS Part 1 listening test"),
        "agent1", on_progress,
    )
    blueprint: IELTSBlueprint = r1.final_output
    await status("Agent 1 done. Running Agent 2 (questions & answers)...")

    r2 = await _run_with_retry(
        lambda: Runner.run(question_agent, blueprint.model_dump_json()),
        "agent2", on_progress,
    )
    question_set: IELTSQuestionSet = r2.final_output
    await status("Agent 2 done.")
    if on_progress:
        await on_progress("questions", question_set.model_dump())

    return blueprint, question_set


async def run_tts_stage(
    blueprint: IELTSBlueprint,
    question_set: IELTSQuestionSet,
    on_progress: ProgressCallback = None,
) -> IELTSTTSScript:
    """Run Agent 3 (TTS script)."""

    async def status(msg: str) -> None:
        if on_progress:
            await on_progress("status", {"message": msg})

    await status("Running Agent 3 (TTS script)...")
    tts_input = json.dumps({
        "question_set": question_set.model_dump(),
        "blueprint_context": {
            "topic": blueprint.topic,
            "scenario": blueprint.scenario,
            "speaker_a_name": blueprint.speaker_a_name,
            "speaker_a_role": blueprint.speaker_a_role,
            "speaker_a_gender": blueprint.speaker_a_gender,
            "speaker_b_name": blueprint.speaker_b_name,
            "speaker_b_role": blueprint.speaker_b_role,
            "speaker_b_gender": blueprint.speaker_b_gender,
            "question_groups": [g.model_dump() for g in blueprint.question_groups],
        },
    })
    r3 = await _run_with_retry(
        lambda: Runner.run(tts_agent, tts_input),
        "agent3", on_progress,
    )
    tts_script: IELTSTTSScript = r3.final_output
    await status("Agent 3 done.")
    return tts_script


async def run_audio_stage(
    tts_script: IELTSTTSScript,
    on_progress: ProgressCallback = None,
) -> str:
    """Run audio generation + S3 upload. Returns CDN URL."""

    async def status(msg: str) -> None:
        if on_progress:
            await on_progress("status", {"message": msg})

    await status("Generating audio and uploading to S3...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_folder = os.getenv("S3_BASE_FOLDER", "dev/ielts").rstrip("/")
    s3_key = f"{base_folder}/part1/ielts_part1_{timestamp}.wav"
    cdn_url: str = await _run_with_retry(
        lambda: asyncio.to_thread(generate_and_upload_to_s3, tts_script, s3_key),
        "audio", on_progress,
    )
    await status("Audio uploaded.")
    if on_progress:
        await on_progress("audio", {"cdn_url": cdn_url})
    return cdn_url


async def run_qa_stage(
    question_set: IELTSQuestionSet,
    tts_script: IELTSTTSScript,
    cdn_url: str,
    on_progress: ProgressCallback = None,
) -> Any:
    """Run Agent 4 (quality validation). Publishes validation event with done=True."""

    async def status(msg: str) -> None:
        if on_progress:
            await on_progress("status", {"message": msg})

    await status("Running Agent 4 (validation)...")
    validation_input = json.dumps({
        "question_set": question_set.model_dump(),
        "tts_script": tts_script.model_dump(),
        "cdn_url": cdn_url,
    })
    r4 = await _run_with_retry(
        lambda: Runner.run(qa_agent, validation_input),
        "agent4", on_progress,
    )
    if on_progress:
        await on_progress("validation", {"result": r4.final_output.model_dump()}, done=True)
    return r4.final_output


async def run_pipeline(on_progress: ProgressCallback = None) -> str:
    """Standalone convenience wrapper: runs all 4 stages sequentially.

    Returns CDN URL of the generated audio.
    """
    blueprint, question_set = await run_qna_stage(on_progress)
    tts_script = await run_tts_stage(blueprint, question_set, on_progress)
    cdn_url = await run_audio_stage(tts_script, on_progress)
    await run_qa_stage(question_set, tts_script, cdn_url, on_progress)
    return cdn_url
