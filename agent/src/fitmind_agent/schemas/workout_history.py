from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


MuscleGroup = Literal[
    "chest",
    "back",
    "legs",
    "shoulders",
    "arms",
    "core",
    "full_body",
    "cardio",
    "other",
]


class WorkoutHistoryFilters(BaseModel):
    start_date: date
    end_date: date
    muscle_group: MuscleGroup | None = None
    exercise_keyword: str | None = Field(default=None, max_length=100)


class WorkoutHistoryParsePayload(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    muscle_group: MuscleGroup | None = None
    exercise_keyword: str | None = Field(default=None, max_length=100)


class WorkoutHistoryItemRead(BaseModel):
    exercise_name: str
    exercise_type: str
    sets_count: int | None = None
    reps_text: str | None = None
    weight_text: str | None = None
    duration_text: str | None = None
    distance_text: str | None = None
    raw_text: str | None = None
    muscle_groups: list[MuscleGroup] = Field(default_factory=list)


class WorkoutHistoryRecordRead(BaseModel):
    id: int
    record_date: date
    session_name: str | None = None
    duration_minutes: int | None = None
    completion_status: str
    perceived_exertion: int | None = None
    energy_level: int | None = None
    mood: str | None = None
    raw_text: str
    items: list[WorkoutHistoryItemRead] = Field(default_factory=list)


class WorkoutHistorySummary(BaseModel):
    record_count: int
    training_day_count: int
    completed_record_count: int
    total_duration_minutes: int | None = None
    strength_sets_count: int
    cardio_item_count: int


class WorkoutHistoryPagination(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int


class WorkoutHistoryResponse(BaseModel):
    filters: WorkoutHistoryFilters
    summary: WorkoutHistorySummary
    records: list[WorkoutHistoryRecordRead]
    pagination: WorkoutHistoryPagination
