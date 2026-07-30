from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datetime import date
from datetime import timedelta
from decimal import Decimal
from typing import Any

from fitmind_agent.db.session import SessionLocal
from fitmind_agent.domain.workout_taxonomy import MUSCLE_GROUP_LABELS
from fitmind_agent.domain.workout_taxonomy import resolve_muscle_groups
from fitmind_agent.repositories.nutrition import BodyStatusRecordRepository
from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.weekly_analytics import DailyMetricSnapshot
from fitmind_agent.schemas.weekly_analytics import MetricComparison
from fitmind_agent.schemas.weekly_analytics import MuscleGroupDistribution
from fitmind_agent.schemas.weekly_analytics import NutritionComparison
from fitmind_agent.schemas.weekly_analytics import NutritionMetrics
from fitmind_agent.schemas.weekly_analytics import RecoveryComparison
from fitmind_agent.schemas.weekly_analytics import RecoveryMetrics
from fitmind_agent.schemas.weekly_analytics import TrainingComparison
from fitmind_agent.schemas.weekly_analytics import TrainingMetrics
from fitmind_agent.schemas.weekly_analytics import WeeklyAnalyticsResponse
from fitmind_agent.schemas.weekly_analytics import WeeklyCoverage
from fitmind_agent.schemas.weekly_analytics import WeeklyCoverageSnapshot
from fitmind_agent.schemas.weekly_analytics import WeeklyDailyPoint
from fitmind_agent.schemas.weekly_analytics import WeeklyPeriodComparison
from fitmind_agent.schemas.weekly_analytics import WeeklyPeriodRange


WEEKDAY_LABELS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


class WeeklyAnalyticsValidationError(ValueError):
    pass


class WeeklyAnalyticsQueryError(RuntimeError):
    pass


class WeeklyAnalyticsService:
    def build_period(
        self,
        *,
        anchor_date: date | None = None,
        today: date | None = None,
    ) -> WeeklyPeriodComparison:
        current_date = today or date.today()
        anchor = anchor_date or current_date
        if anchor > current_date:
            raise WeeklyAnalyticsValidationError("暂不支持查询未来周的趋势数据。")

        week_start = anchor - timedelta(days=anchor.weekday())
        active_week_start = current_date - timedelta(days=current_date.weekday())
        is_current_week = week_start == active_week_start
        week_end = current_date if is_current_week else week_start + timedelta(days=6)
        day_count = (week_end - week_start).days + 1
        previous_start = week_start - timedelta(days=7)
        previous_end = previous_start + timedelta(days=day_count - 1)
        return WeeklyPeriodComparison(
            anchor_date=anchor,
            is_current_week=is_current_week,
            current=WeeklyPeriodRange(
                start_date=week_start,
                end_date=week_end,
                day_count=day_count,
            ),
            previous=WeeklyPeriodRange(
                start_date=previous_start,
                end_date=previous_end,
                day_count=day_count,
            ),
        )

    def analyze(
        self,
        *,
        user_id: int,
        anchor_date: date | None = None,
    ) -> WeeklyAnalyticsResponse:
        result = None
        for event in self.stream_analyze(user_id=user_id, anchor_date=anchor_date):
            if event["kind"] == "result":
                result = event["result"]
        if result is None:
            raise WeeklyAnalyticsQueryError("周报统计未生成结果。")
        return result

    def stream_analyze(
        self,
        *,
        user_id: int,
        anchor_date: date | None = None,
    ) -> Iterator[dict[str, Any]]:
        period = self.build_period(anchor_date=anchor_date)
        tasks = {
            "workouts": self._query_workouts,
            "nutrition": self._query_nutrition,
            "body_status": self._query_body_status,
        }
        datasets: dict[str, list[dict[str, Any]]] = {
            "workouts": [],
            "nutrition": [],
            "body_status": [],
        }

        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="fitmind-weekly") as executor:
            future_map = {
                executor.submit(
                    query,
                    user_id=user_id,
                    start_date=period.previous.start_date,
                    end_date=period.current.end_date,
                ): name
                for name, query in tasks.items()
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    datasets[name] = future.result()
                except Exception as exc:
                    yield {"kind": "dataset_error", "dataset": name, "error": str(exc)}
                    raise WeeklyAnalyticsQueryError(f"{name} 数据查询失败：{exc}") from exc
                yield {
                    "kind": "dataset",
                    "dataset": name,
                    "count": len(datasets[name]),
                }

        yield {
            "kind": "result",
            "result": self._build_response(period=period, datasets=datasets),
        }

    @staticmethod
    def _query_workouts(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = WorkoutRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "record_date": record.record_date,
                    "completion_status": record.completion_status,
                    "duration_minutes": record.duration_minutes,
                    "session_name": record.session_name,
                    "raw_text": record.raw_text,
                    "items": [
                        {
                            "exercise_name": item.exercise_name,
                            "exercise_type": item.exercise_type,
                            "sets_count": item.sets_count,
                            "raw_text": item.raw_text,
                        }
                        for item in record.items
                    ],
                }
                for record in records
            ]

    @staticmethod
    def _query_nutrition(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = NutritionRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "record_date": record.record_date,
                    "calories": record.calories_estimate,
                    "protein_g": record.protein_g_estimate,
                    "carbs_g": record.carbs_g_estimate,
                    "fat_g": record.fat_g_estimate,
                }
                for record in records
            ]

    @staticmethod
    def _query_body_status(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = BodyStatusRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "record_date": record.record_date,
                    "sleep_hours": record.sleep_hours,
                    "fatigue_level": record.fatigue_level,
                    "stress_level": record.stress_level,
                    "soreness_level": record.soreness_level,
                    "body_weight_kg": record.body_weight_kg,
                }
                for record in records
            ]

    def _build_response(
        self,
        *,
        period: WeeklyPeriodComparison,
        datasets: dict[str, list[dict[str, Any]]],
    ) -> WeeklyAnalyticsResponse:
        current = self._slice_datasets(datasets, period.current)
        previous = self._slice_datasets(datasets, period.previous)
        current_training = self._summarize_training(current["workouts"])
        previous_training = self._summarize_training(previous["workouts"])
        current_nutrition = self._summarize_nutrition(current["nutrition"])
        previous_nutrition = self._summarize_nutrition(previous["nutrition"])
        current_recovery = self._summarize_recovery(current["body_status"])
        previous_recovery = self._summarize_recovery(previous["body_status"])

        return WeeklyAnalyticsResponse(
            period=period,
            coverage=WeeklyCoverage(
                current=self._coverage(current),
                previous=self._coverage(previous),
            ),
            training=TrainingComparison(
                current=current_training,
                previous=previous_training,
                changes=self._compare_models(current_training, previous_training),
            ),
            nutrition=NutritionComparison(
                current=current_nutrition,
                previous=previous_nutrition,
                changes=self._compare_models(current_nutrition, previous_nutrition),
            ),
            recovery=RecoveryComparison(
                current=current_recovery,
                previous=previous_recovery,
                changes=self._compare_models(current_recovery, previous_recovery),
            ),
            daily_series=self._build_daily_series(period, current, previous),
            muscle_distribution=self._build_muscle_distribution(
                current["workouts"],
                previous["workouts"],
            ),
        )

    @staticmethod
    def _slice_datasets(
        datasets: dict[str, list[dict[str, Any]]],
        period: WeeklyPeriodRange,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            name: [
                item
                for item in items
                if period.start_date <= item["record_date"] <= period.end_date
            ]
            for name, items in datasets.items()
        }

    @staticmethod
    def _coverage(datasets: dict[str, list[dict[str, Any]]]) -> WeeklyCoverageSnapshot:
        return WeeklyCoverageSnapshot(
            workout_days=len({item["record_date"] for item in datasets["workouts"]}),
            nutrition_days=len({item["record_date"] for item in datasets["nutrition"]}),
            body_status_days=len({item["record_date"] for item in datasets["body_status"]}),
        )

    @staticmethod
    def _summarize_training(records: list[dict[str, Any]]) -> TrainingMetrics:
        durations = [
            int(record["duration_minutes"])
            for record in records
            if record["duration_minutes"] is not None
        ]
        items = [item for record in records for item in record["items"]]
        return TrainingMetrics(
            record_count=len(records),
            training_day_count=len({record["record_date"] for record in records}),
            completed_record_count=sum(
                record["completion_status"] == "completed" for record in records
            ),
            total_duration_minutes=sum(durations) if durations else None,
            strength_sets_count=sum(
                int(item["sets_count"] or 0)
                for item in items
                if item["exercise_type"] == "strength"
            ),
            cardio_item_count=sum(item["exercise_type"] == "cardio" for item in items),
        )

    def _summarize_nutrition(self, records: list[dict[str, Any]]) -> NutritionMetrics:
        return NutritionMetrics(
            record_days=len({record["record_date"] for record in records}),
            average_calories=self._average(records, "calories"),
            average_protein_g=self._average(records, "protein_g"),
            average_carbs_g=self._average(records, "carbs_g"),
            average_fat_g=self._average(records, "fat_g"),
        )

    def _summarize_recovery(self, records: list[dict[str, Any]]) -> RecoveryMetrics:
        weight_points = sorted(
            (
                (record["record_date"], self._to_float(record["body_weight_kg"]))
                for record in records
                if record["body_weight_kg"] is not None
            ),
            key=lambda item: item[0],
        )
        weight_change = None
        if len(weight_points) >= 2:
            weight_change = round(weight_points[-1][1] - weight_points[0][1], 2)
        return RecoveryMetrics(
            record_days=len({record["record_date"] for record in records}),
            average_sleep_hours=self._average(records, "sleep_hours"),
            average_fatigue_level=self._average(records, "fatigue_level"),
            average_stress_level=self._average(records, "stress_level"),
            average_soreness_level=self._average(records, "soreness_level"),
            body_weight_change_kg=weight_change,
        )

    @staticmethod
    def _average(records: list[dict[str, Any]], key: str) -> float | None:
        values = [
            WeeklyAnalyticsService._to_float(record[key])
            for record in records
            if record.get(key) is not None
        ]
        return round(sum(values) / len(values), 2) if values else None

    @staticmethod
    def _to_float(value: Any) -> float:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @staticmethod
    def _compare_models(current: Any, previous: Any) -> dict[str, MetricComparison]:
        current_values = current.model_dump()
        previous_values = previous.model_dump()
        return {
            key: WeeklyAnalyticsService._compare_values(
                current_values.get(key),
                previous_values.get(key),
            )
            for key in current_values
        }

    @staticmethod
    def _compare_values(current: Any, previous: Any) -> MetricComparison:
        current_value = float(current) if current is not None else None
        previous_value = float(previous) if previous is not None else None
        if current_value is None or previous_value is None:
            return MetricComparison(current=current_value, previous=previous_value)
        delta = round(current_value - previous_value, 2)
        delta_percent = (
            round(delta / abs(previous_value) * 100, 2) if previous_value != 0 else None
        )
        return MetricComparison(
            current=current_value,
            previous=previous_value,
            delta=delta,
            delta_percent=delta_percent,
        )

    def _build_daily_series(
        self,
        period: WeeklyPeriodComparison,
        current: dict[str, list[dict[str, Any]]],
        previous: dict[str, list[dict[str, Any]]],
    ) -> list[WeeklyDailyPoint]:
        points = []
        for offset, weekday in enumerate(WEEKDAY_LABELS):
            current_date = period.current.start_date + timedelta(days=offset)
            previous_date = period.previous.start_date + timedelta(days=offset)
            current_snapshot = (
                self._build_daily_snapshot(current_date, current)
                if current_date <= period.current.end_date
                else None
            )
            previous_snapshot = (
                self._build_daily_snapshot(previous_date, previous)
                if previous_date <= period.previous.end_date
                else None
            )
            points.append(
                WeeklyDailyPoint(
                    day_index=offset + 1,
                    weekday=weekday,
                    current_date=current_date,
                    previous_date=previous_date,
                    current=current_snapshot,
                    previous=previous_snapshot,
                )
            )
        return points

    def _build_daily_snapshot(
        self,
        target_date: date,
        datasets: dict[str, list[dict[str, Any]]],
    ) -> DailyMetricSnapshot:
        workouts = [
            item for item in datasets["workouts"] if item["record_date"] == target_date
        ]
        nutrition = next(
            (item for item in datasets["nutrition"] if item["record_date"] == target_date),
            None,
        )
        body_status = next(
            (item for item in datasets["body_status"] if item["record_date"] == target_date),
            None,
        )
        training = self._summarize_training(workouts)
        return DailyMetricSnapshot(
            workout_records=training.record_count,
            duration_minutes=training.total_duration_minutes,
            strength_sets=training.strength_sets_count,
            cardio_items=training.cardio_item_count,
            calories=self._optional_float(nutrition, "calories"),
            protein_g=self._optional_float(nutrition, "protein_g"),
            sleep_hours=self._optional_float(body_status, "sleep_hours"),
            fatigue_level=self._optional_float(body_status, "fatigue_level"),
            body_weight_kg=self._optional_float(body_status, "body_weight_kg"),
        )

    @staticmethod
    def _optional_float(record: dict[str, Any] | None, key: str) -> float | None:
        if record is None or record.get(key) is None:
            return None
        return WeeklyAnalyticsService._to_float(record[key])

    @staticmethod
    def _build_muscle_distribution(
        current_records: list[dict[str, Any]],
        previous_records: list[dict[str, Any]],
    ) -> list[MuscleGroupDistribution]:
        current_counts = WeeklyAnalyticsService._count_muscle_groups(current_records)
        previous_counts = WeeklyAnalyticsService._count_muscle_groups(previous_records)
        return [
            MuscleGroupDistribution(
                muscle_group=group,
                label=label,
                current_count=current_counts[group],
                previous_count=previous_counts[group],
            )
            for group, label in MUSCLE_GROUP_LABELS.items()
            if current_counts[group] or previous_counts[group]
        ]

    @staticmethod
    def _count_muscle_groups(records: list[dict[str, Any]]) -> Counter:
        counts: Counter = Counter()
        for record in records:
            if record["items"]:
                for item in record["items"]:
                    text = " ".join(
                        value
                        for value in (item["exercise_name"], item["raw_text"])
                        if isinstance(value, str)
                    )
                    counts.update(
                        resolve_muscle_groups(
                            text,
                            exercise_type=item["exercise_type"],
                        )
                    )
            else:
                text = " ".join(
                    value
                    for value in (record["session_name"], record["raw_text"])
                    if isinstance(value, str)
                )
                counts.update(resolve_muscle_groups(text))
        return counts
