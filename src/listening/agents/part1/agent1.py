import asyncio
from enum import Enum

from agents import Agent, Runner
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


async def create_skeleton_agent() -> Agent:
    """Build a Skeleton Planner agent with exclusion list injected into prompt."""
    from listening.agents.part1.history import get_exclusion_context

    exclusion = await get_exclusion_context()
    prompt = AGENT_1.replace("{exclusion_list}", exclusion)
    return Agent(
        name="Skeleton Planner",
        model=MODEL,
        instructions=prompt,
        output_type=IELTSBlueprint,
    )


async def main():
    from listening.agents.part1.history import save_blueprint

    agent = await create_skeleton_agent()
    result = await Runner.run(agent, "")
    await save_blueprint(result.final_output)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
