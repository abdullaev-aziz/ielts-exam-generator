import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import asyncio
import json
from datetime import datetime
from agents import Runner
from agent1 import skeleton_agent, IELTSBlueprint
from agent2 import question_agent, IELTSQuestionSet
from agent3 import tts_agent, IELTSTTSScript
from agent4 import qa_agent
from ielts_audio_generator import generate_and_upload_to_s3


async def run_pipeline(on_progress=None):
    async def status(msg):
        if on_progress:
            await on_progress("status", {"message": msg})

    await status("Pipeline started, running Agent 1 (blueprint)...")

    # Step 1: Blueprint
    r1 = await Runner.run(skeleton_agent, "Create IELTS Part 1 listening test")
    blueprint: IELTSBlueprint = r1.final_output
    await status("Agent 1 completed successfully. Running Agent 2 (questions & answers)...")

    # Step 2: Questions + answers
    r2 = await Runner.run(question_agent, blueprint.model_dump_json())
    question_set: IELTSQuestionSet = r2.final_output
    await status("Agent 2 completed successfully. Running Agent 3 (TTS script)...")
    if on_progress:
        await on_progress("questions", question_set.model_dump())

    # Step 3: TTS script (needs both question set and blueprint context)
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
    r3 = await Runner.run(tts_agent, tts_input)
    tts_script: IELTSTTSScript = r3.final_output
    await status("Agent 3 completed successfully. Generating and uploading audio...")

    # Step 4: Audio generation + S3 upload
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_folder = os.getenv("S3_BASE_FOLDER", "dev/ielts").rstrip("/")
    s3_key = f"{base_folder}/part1/ielts_part1_{timestamp}.wav"
    cdn_url = await asyncio.to_thread(generate_and_upload_to_s3, tts_script, s3_key)
    await status("Audio uploaded successfully. Running Agent 4 (validation)...")
    if on_progress:
        await on_progress("audio", {"cdn_url": cdn_url})

    # Step 5: Validation
    validation_input = json.dumps({
        "question_set": question_set.model_dump(),
        "tts_script": tts_script.model_dump(),
    })
    r4 = await Runner.run(qa_agent, validation_input)
    if on_progress:
        await on_progress("validation", {"result": r4.final_output}, done=True)

    return cdn_url

