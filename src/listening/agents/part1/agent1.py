from enum import Enum

from agents import Agent
from pydantic import BaseModel

from listening.agents.part1.config import MODEL
from listening.agents.part1.prompts import AGENT_1

class Gender(str, Enum):
    WOMAN = "WOMAN"
    MAN = "MAN"

class QuestionType(str, Enum):
    form_completion = "form_completion"
    matching = "matching"

class QuestionGroup(BaseModel):
    part_number: int
    question_range: list[int]
    question_type: QuestionType
    word_limit: int | None
    context_description: str

class PlannedAnswerField(BaseModel):
    question_number: int
    field_type: str

class IELTSBlueprint(BaseModel):
    topic: str
    scenario: str
    speaker_a_name: str
    speaker_a_role: str
    speaker_a_gender: Gender
    speaker_b_name: str
    speaker_b_role: str
    speaker_b_gender: Gender
    question_groups: list[QuestionGroup]
    planned_answer_fields: list[PlannedAnswerField]

skeleton_agent = Agent(
    name="Skeleton Planner",
    model=MODEL,
    instructions=AGENT_1,
    output_type=IELTSBlueprint
)

skeleton_tool = skeleton_agent.as_tool(
    tool_name="generate_skeleton",
    tool_description="Generate IELTS test skeleton"
)

