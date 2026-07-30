from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from fitmind_agent.schemas.workout_history import MuscleGroup


class WeeklyPeriodRange(BaseModel):
    start_date: date
    end_date: date
    day_count: int = Field(ge=1, le=7)


class WeeklyPeriodComparison(BaseModel):
    anchor_date: date
    is_current_week: bool
    current: WeeklyPeriodRange
    previous: WeeklyPeriodRange


class MetricComparison(BaseModel):
    current: float | None = None
    previous: float | None = None
    delta: float | None = None
    delta_percent: float | None = None


class TrainingMetrics(BaseModel):
    record_count: int = 0
    training_day_count: int = 0
    completed_record_count: int = 0
    total_duration_minutes: int | None = None
    strength_sets_count: int = 0
    cardio_item_count: int = 0


class NutritionMetrics(BaseModel):
    record_days: int = 0
    average_calories: float | None = None
    average_protein_g: float | None = None
    average_carbs_g: float | None = None
    average_fat_g: float | None = None


class RecoveryMetrics(BaseModel):
    record_days: int = 0
    average_sleep_hours: float | None = None
    average_fatigue_level: float | None = None
    average_stress_level: float | None = None
    average_soreness_level: float | None = None
    body_weight_change_kg: float | None = None


class TrainingComparison(BaseModel):
    current: TrainingMetrics
    previous: TrainingMetrics
    changes: dict[str, MetricComparison]


class NutritionComparison(BaseModel):
    current: NutritionMetrics
    previous: NutritionMetrics
    changes: dict[str, MetricComparison]


class RecoveryComparison(BaseModel):
    current: RecoveryMetrics
    previous: RecoveryMetrics
    changes: dict[str, MetricComparison]


class WeeklyCoverageSnapshot(BaseModel):
    workout_days: int = 0
    nutrition_days: int = 0
    body_status_days: int = 0


class WeeklyCoverage(BaseModel):
    current: WeeklyCoverageSnapshot
    previous: WeeklyCoverageSnapshot


class DailyMetricSnapshot(BaseModel):
    workout_records: int | None = None
    duration_minutes: int | None = None
    strength_sets: int | None = None
    cardio_items: int | None = None
    calories: float | None = None
    protein_g: float | None = None
    sleep_hours: float | None = None
    fatigue_level: float | None = None
    body_weight_kg: float | None = None


class WeeklyDailyPoint(BaseModel):
    day_index: int = Field(ge=1, le=7)
    weekday: str
    current_date: date
    previous_date: date
    current: DailyMetricSnapshot | None = None
    previous: DailyMetricSnapshot | None = None


class MuscleGroupDistribution(BaseModel):
    muscle_group: MuscleGroup
    label: str
    current_count: int = 0
    previous_count: int = 0


class WeeklyAnalyticsResponse(BaseModel):
    period: WeeklyPeriodComparison
    coverage: WeeklyCoverage
    training: TrainingComparison
    nutrition: NutritionComparison
    recovery: RecoveryComparison
    daily_series: list[WeeklyDailyPoint]
    muscle_distribution: list[MuscleGroupDistribution]
