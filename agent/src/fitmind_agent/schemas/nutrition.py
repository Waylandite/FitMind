from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class NutritionRecordPayload(BaseModel):
    has_content: bool = False
    raw_text: str | None = None
    calories_estimate: Decimal | None = Field(default=None, ge=0)
    protein_g_estimate: Decimal | None = Field(default=None, ge=0)
    carbs_g_estimate: Decimal | None = Field(default=None, ge=0)
    fat_g_estimate: Decimal | None = Field(default=None, ge=0)


class BodyStatusRecordPayload(BaseModel):
    has_content: bool = False
    raw_text: str | None = None
    sleep_hours: Decimal | None = Field(default=None, ge=0, le=24)
    fatigue_level: int | None = Field(default=None, ge=1, le=10)
    stress_level: int | None = Field(default=None, ge=1, le=10)
    soreness_level: int | None = Field(default=None, ge=1, le=10)
    body_weight_kg: Decimal | None = Field(default=None, ge=0)
    mood: str | None = None


class NutritionSleepRecordPayload(BaseModel):
    record_date: date
    nutrition: NutritionRecordPayload = Field(default_factory=NutritionRecordPayload)
    body_status: BodyStatusRecordPayload = Field(default_factory=BodyStatusRecordPayload)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    summary_text: str = ""


class NutritionSleepPersistResult(BaseModel):
    record_date: date
    nutrition_record_id: int | None = None
    body_status_record_id: int | None = None
    saved_nutrition: bool = False
    saved_body_status: bool = False


class NutritionSleepWorkflowResult(BaseModel):
    handled: bool
    action: Literal["recorded", "ignored"]
    reply: str
    payload: NutritionSleepRecordPayload | None = None
    persist_result: NutritionSleepPersistResult | None = None
