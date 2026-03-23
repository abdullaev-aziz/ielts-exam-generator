from agents import Agent, Runner
from config import MODEL
from prompts import AGENT_2

qa_agent = Agent(
    name="Quality Checker",
    instructions="Validate IELTS content quality",
    # output_type=
)

qa_tool = qa_agent.as_tool(
    tool_name="validate_exam",
    tool_description="Validate IELTS exam"
)