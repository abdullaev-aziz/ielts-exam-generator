from agents import Agent
from config import MODEL
from prompts import AGENT_2
from pydantic import BaseModel
from enum import Enum


class AnswerType(str, Enum):
    NAME = "NAME"
    NUMBER = "NUMBER"
    DATE = "DATE"
    TIME = "TIME"
    ADDRESS = "ADDRESS"
    POSTCODE = "POSTCODE"
    MONEY = "MONEY"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    WORD = "WORD"
    PHRASE = "PHRASE"


class QuestionFormat(str, Enum):
    fill_blank = "fill_blank"
    matching = "matching"


class Question(BaseModel):
    q: int
    prompt: str
    answer_type: AnswerType
    word_limit: int
    format: QuestionFormat


class DistractorTechnique(str, Enum):
    correction_trap = "correction_trap"
    spelling_protocol = "spelling_protocol"
    number_confusion = "number_confusion"
    decoy_alternative = "decoy_alternative"
    paraphrase_repetition = "paraphrase_repetition"
    hesitation_filler = "hesitation_filler"


class Speaker(str, Enum):
    NARRATOR = "NARRATOR"
    MAN = "MAN"
    WOMAN = "WOMAN"


class DialogueLine(BaseModel):
    speaker: Speaker
    text: str
    target_question: int | None = None
    distractor_techniques: list[DistractorTechnique] = []


class AnswerKeyEntry(BaseModel):
    question_number: int
    answer: str
    distractor: str | None = None
    distractor_technique: DistractorTechnique | None = None


class IELTSQuestionSet(BaseModel):
    questions: list[Question]
    answer_key: list[AnswerKeyEntry]
    dialogue: list[DialogueLine]
    correction_trap_count: int
    spelling_protocol_count: int


question_agent = Agent(
    name="Question Writer",
    model=MODEL,
    instructions=AGENT_2,
    output_type=IELTSQuestionSet,
)

question_tool = question_agent.as_tool(
    tool_name="generate_questions",
    tool_description="Generate IELTS Part 1 questions, answers, and dialogue from a blueprint. Input: the full IELTSBlueprint JSON from the skeleton generator.",
)
