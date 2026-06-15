from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class WorkoutPlanDraftPayload(BaseModel):
    title: str | None = None
    plan_date: date | None = None
    raw_text: str
    source: Literal["manual", "agent"] = "manual"
    status: Literal["active", "archived"] = "active"
    remark: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    summary_text: str = ""


class WorkoutPlanPersistResult(BaseModel):
    workout_plan_id: int
    title: str | None = None
    plan_date: date | None = None


class WorkoutPlanWorkflowResult(BaseModel):
    handled: bool
    action: Literal["draft_created", "draft_updated", "confirmed", "cancelled", "ignored"]
    reply: str
    draft_id: int | None = None
    draft_payload: WorkoutPlanDraftPayload | None = None
    persist_result: WorkoutPlanPersistResult | None = None
