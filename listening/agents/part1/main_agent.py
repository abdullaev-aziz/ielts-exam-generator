import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import asyncio
from agents import Agent, Runner
from agent1 import skeleton_tool
from agent2 import question_tool, IELTSQuestionSet
from agent3 import tts_tool, IELTSTTSScript
import json
from agent4 import qa_tool
from ielts_audio_generator import generate_audio

orchestrator = Agent(
    name="IELTS Orchestrator",
    instructions="""
You generate IELTS exam content by orchestrating four tools in strict sequence.

Steps:
1. Call generate_skeleton with the user's topic to get an IELTSBlueprint.
2. Call generate_questions and pass the COMPLETE IELTSBlueprint JSON output from step 1 as the input. Do not summarise or truncate it.
3. Call generate_tts_script and pass TWO things combined into a single input:
   a) The COMPLETE IELTSQuestionSet JSON from step 2
   b) The following fields from the IELTSBlueprint (step 1): topic, scenario, speaker_a_name, speaker_a_role, speaker_a_gender, speaker_b_name, speaker_b_role, speaker_b_gender, and question_groups (with question_range for each group)
   Include both in the input — Agent 3 needs the blueprint context to write narrator lines and split dialogue between question groups.
4. Call validate_exam and pass the complete outputs from all previous steps.

Always use tools in this exact order. Pass complete JSON outputs between steps — never summarise or omit fields.
""",
    tools=[
        skeleton_tool,
        question_tool,
        tts_tool,
        # qa_tool
    ],
    output_type= IELTSTTSScript,
)
async def main():
    result = await Runner.run(
        orchestrator,
        "Create IELTS listening",
    )

    with open("../../../tts_events1.json", "w") as f:
        json.dump(result.final_output.model_dump(), f, indent=2)

    print("Saved to tts_events.json")

    await asyncio.to_thread(generate_audio, result.final_output, "../../../ielts_part1.wav")


if __name__ == "__main__":
    asyncio.run(main())
