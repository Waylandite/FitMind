from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class UserProfileUpsert(BaseModel):
    gender: str | None = None
    birth_date: date | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    target_weight_kg: Decimal | None = None
    goal_type: str | None = None
    training_level: str | None = None
    injury_notes: str | None = None
    medical_notes: str | None = None
    diet_preference: str | None = None
    preferred_training_days: str | None = None
    remark: str | None = None


class UserProfileRead(BaseModel):
    id: int
    user_id: int
    gender: str | None
    birth_date: date | None
    height_cm: Decimal | None
    weight_kg: Decimal | None
    target_weight_kg: Decimal | None
    goal_type: str | None
    training_level: str | None
    injury_notes: str | None
    medical_notes: str | None
    diet_preference: str | None
    preferred_training_days: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
