from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class ClarificationInput(BaseModel):
    id: int
    action: Literal["select", "cancel"]
    selected_intent: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int | None = Field(default=None, description="Optional user identifier for persistence.")
    thread_id: str = Field(default="test-thread", description="Conversation thread identifier.")
    message: str = Field(..., min_length=1, description="User input text.")
    system_prompt: str | None = Field(default=None, description="Optional system prompt override.")
    model: str | None = Field(default=None, description="Optional LLM model override.")
    temperature: float | None = Field(default=None, description="Optional sampling temperature override.")
    persist_log: bool = Field(
        default=False,
        description="Whether to write user/assistant messages into conversation_logs.",
    )
    clarification: ClarificationInput | None = None
    _original_message: str | None = PrivateAttr(default=None)


class ChatResponse(BaseModel):
    user_id: int | None
    thread_id: str
    session_id: int | None = None
    intent: str
    intent_confidence: float | None = None
    intent_source: str | None = None
    module_name: str | None = None
    module_status: str | None = None
    model: str | None = None
    reply: str
    clarification: dict | None = None
