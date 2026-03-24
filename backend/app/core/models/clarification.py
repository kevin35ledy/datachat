from __future__ import annotations
from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    context: str = ""
    suggestions: list[str] = Field(default_factory=list)


class ClarificationRequest(BaseModel):
    nl_text: str


class ClarificationResponse(BaseModel):
    questions: list[ClarificationQuestion] = Field(default_factory=list)
