from enum import Enum

from agents import Agent
from pydantic import BaseModel

from listening.agents.part1.agent2 import Speaker
from listening.agents.part1.config import MODEL
from listening.agents.part1.prompts import AGENT_3


class EventType(str, Enum):
    speech = "speech"
    silence = "silence"


class SilenceType(str, Enum):
    look_questions_group_1 = "look_questions_group_1"
    before_dialogue_group_1 = "before_dialogue_group_1"
    after_dialogue_group_1 = "after_dialogue_group_1"
    look_questions_group_2 = "look_questions_group_2"
    before_dialogue_group_2 = "before_dialogue_group_2"
    after_dialogue_group_2 = "after_dialogue_group_2"
    check_answers = "check_answers"
    micro_pause = "micro_pause"


class TTSEvent(BaseModel):
    event_type: EventType
    speaker: Speaker | None = None
    text: str | None = None
    silence_type: SilenceType | None = None


SILENCE_DURATIONS = {
    SilenceType.look_questions_group_1: 23.0,
    SilenceType.before_dialogue_group_1: 4.0,
    SilenceType.after_dialogue_group_1: 4.0,
    SilenceType.look_questions_group_2: 35.0,
    SilenceType.before_dialogue_group_2: 3.0,
    SilenceType.after_dialogue_group_2: 3.0,
    SilenceType.check_answers: 30.0,
    SilenceType.micro_pause: 0.25,
}


class IELTSTTSScript(BaseModel):
    events: list[TTSEvent]

    def to_events(self) -> list[tuple]:
        """Convert to the tuple format used by ielts_audio_generator.py."""
        result = []
        for e in self.events:
            if e.event_type == EventType.speech:
                result.append((e.speaker.value, e.text))
            else:
                result.append((None, SILENCE_DURATIONS[e.silence_type]))
        return result


tts_agent = Agent(
    name="TTS Script Generator",
    model=MODEL,
    instructions=AGENT_3,
    output_type=IELTSTTSScript,
)

tts_tool = tts_agent.as_tool(
    tool_name="generate_tts_script",
    tool_description="Generate full TTS event script with narrator lines, silences, and polished dialogue. Input: IELTSQuestionSet JSON + blueprint speaker info.",
)
