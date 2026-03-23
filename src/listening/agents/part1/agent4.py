from agents import Agent
from pydantic import BaseModel

from listening.agents.part1.config import MODEL
from listening.agents.part1.prompts import AGENT_4


class IELTSValidation(BaseModel):
    valid: bool
    issues: list[str]
    summary: str


qa_agent = Agent(
    name="Quality Checker",
    model=MODEL,
    instructions=AGENT_4,
    output_type=IELTSValidation,
)

qa_tool = qa_agent.as_tool(
    tool_name="validate_exam",
    tool_description="Validate IELTS exam content against Cambridge standards. Input: JSON with question_set, tts_script, and cdn_url.",
)