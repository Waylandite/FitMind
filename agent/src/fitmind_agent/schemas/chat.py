from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
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


class ChatResponse(BaseModel):
    user_id: int | None
    thread_id: str
    session_id: int | None = None
    intent: str
    model: str | None = None
    reply: str
