from typing import Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "developer", "tool"]
    content: str = Field(..., min_length=1)


class LLMChatRequest(BaseModel):
    messages: list[LLMMessage]
    model: str | None = None
    temperature: float | None = None


class LLMChatResponse(BaseModel):
    model: str
    content: str
    raw_response: dict
