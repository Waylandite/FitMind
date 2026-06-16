from datetime import date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkoutExerciseDraft(BaseModel):
    exercise_name: str = ""
    exercise_type: Literal["strength", "cardio", "mobility", "other"] = "strength"
    sets_count: int | None = Field(default=None, ge=1)
    reps_text: str | None = None
    weight_text: str | None = None
    duration_text: str | None = None
    distance_text: str | None = None
    raw_text: str | None = None
    remark: str | None = None


class WorkoutRecordDraftPayload(BaseModel):
    record_date: date
    session_name: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    completion_status: Literal["completed", "partial", "skipped"] = "completed"
    perceived_exertion: int | None = Field(default=None, ge=1, le=10)
    energy_level: int | None = Field(default=None, ge=1, le=10)
    mood: str | None = None
    exercises: list[WorkoutExerciseDraft] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    summary_text: str = ""


class WorkoutRecordDraftRead(BaseModel):
    id: int
    user_id: int
    session_id: int | None
    status: str
    raw_text: str
    draft_payload: dict | None
    confidence_score: float | None
    confirmed_at: datetime | None
    workout_record_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkoutPersistResult(BaseModel):
    workout_record_id: int
    item_count: int
    record_date: date
    session_name: str | None = None


class WorkoutRecordWorkflowResult(BaseModel):
    handled: bool
    action: Literal["draft_created", "draft_updated", "confirmed", "cancelled", "ignored"]
    reply: str
    draft_id: int | None = None
    draft_payload: WorkoutRecordDraftPayload | None = None
    persist_result: WorkoutPersistResult | None = None
