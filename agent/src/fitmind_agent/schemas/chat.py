from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Current user identifier from the web app.")
    thread_id: str = Field(..., description="Conversation thread identifier.")
    message: str = Field(..., min_length=1, description="User input text.")


class ChatResponse(BaseModel):
    user_id: str
    thread_id: str
    intent: str
    reply: str
