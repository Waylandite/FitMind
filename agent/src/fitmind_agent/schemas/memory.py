from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class UserDefinedMemoryCreate(BaseModel):
    user_id: int
    memory_key: str = Field(..., min_length=1, max_length=100)
    memory_category: str
    memory_value: str | None = None
    raw_text: str | None = None
    priority: int = 100
    status: str = "active"
    source_conversation_log_id: int | None = None


class UserDefinedMemoryUpdate(BaseModel):
    memory_key: str | None = None
    memory_category: str | None = None
    memory_value: str | None = None
    raw_text: str | None = None
    priority: int | None = None
    status: str | None = None
    source_conversation_log_id: int | None = None


class UserDefinedMemoryRead(BaseModel):
    id: int
    user_id: int
    memory_key: str
    memory_category: str
    memory_value: str | None
    raw_text: str | None
    priority: int
    status: str
    source_conversation_log_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentDerivedMemoryCreate(BaseModel):
    user_id: int
    memory_category: str
    memory_type: str = Field(..., min_length=1, max_length=100)
    summary_text: str = Field(..., min_length=1)
    structured_payload: dict[str, Any] | list[Any] | None = None
    confidence_score: float | None = None
    source_session_id: int | None = None
    source_conversation_log_id: int | None = None
    status: str = "active"
    valid_from: date | None = None
    valid_to: date | None = None


class AgentDerivedMemoryUpdate(BaseModel):
    memory_category: str | None = None
    memory_type: str | None = None
    summary_text: str | None = None
    structured_payload: dict[str, Any] | list[Any] | None = None
    confidence_score: float | None = None
    source_session_id: int | None = None
    source_conversation_log_id: int | None = None
    status: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class AgentDerivedMemoryRead(BaseModel):
    id: int
    user_id: int
    memory_category: str
    memory_type: str
    summary_text: str
    structured_payload: dict[str, Any] | list[Any] | None
    confidence_score: float | None
    source_session_id: int | None
    source_conversation_log_id: int | None
    status: str
    valid_from: date | None
    valid_to: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionCreate(BaseModel):
    user_id: int
    thread_id: str = Field(..., min_length=1, max_length=100)
    session_no: int = 1
    title: str | None = None
    status: str = "active"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    last_message_at: datetime | None = None


class ChatSessionUpdate(BaseModel):
    thread_id: str | None = None
    session_no: int | None = None
    title: str | None = None
    status: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    last_message_at: datetime | None = None


class ChatSessionRead(BaseModel):
    id: int
    user_id: int
    thread_id: str
    session_no: int
    title: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationLogRead(BaseModel):
    id: int
    user_id: int
    thread_id: str
    session_id: int | None
    record_date: date | None
    role: str
    message_text: str
    intent_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionSummaryCreate(BaseModel):
    session_id: int
    user_id: int
    summary_type: str
    summary_text: str = Field(..., min_length=1)
    structured_payload: dict[str, Any] | list[Any] | None = None
    summary_version: int = 1
    source_message_count: int | None = None


class ChatSessionSummaryUpdate(BaseModel):
    summary_type: str | None = None
    summary_text: str | None = None
    structured_payload: dict[str, Any] | list[Any] | None = None
    summary_version: int | None = None
    source_message_count: int | None = None


class ChatSessionSummaryRead(BaseModel):
    id: int
    session_id: int
    user_id: int
    summary_type: str
    summary_text: str
    structured_payload: dict[str, Any] | list[Any] | None
    summary_version: int
    source_message_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
