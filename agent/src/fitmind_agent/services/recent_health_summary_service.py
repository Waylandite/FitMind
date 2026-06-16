from __future__ import annotations

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from typing import Any

from fitmind_agent.db.session import SessionLocal
from fitmind_agent.repositories.nutrition import BodyStatusRecordRepository
from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.repositories.workout import WorkoutPlanRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


@dataclass(frozen=True)
class RecentHealthSummaryResult:
    handled: bool
    action: str
    reply: str
    payload: dict[str, Any] | None = None


class RecentHealthSummaryService:
    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        lookback_days: int = 7,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.lookback_days = lookback_days

    def stream_maybe_handle(
        self,
        *,
        user_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> Iterator[dict[str, Any]]:
        if user_id is None or intent_result.intent != "recent_health_summary":
            yield {
                "kind": "result",
                "result": RecentHealthSummaryResult(handled=False, action="ignored", reply=""),
            }
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days - 1)
        yield self._progress(
            status="queue",
            node="summary_start",
            title="最近健康总结模块已接管",
            detail=f"准备查询 {start_date.isoformat()} 至 {end_date.isoformat()} 的训练、饮食和身体状态。",
        )

        datasets = yield from self._collect_context_stream(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        yield self._progress(
            status="thinking",
            node="summary_llm",
            title="正在分析最近一周数据",
            detail="已汇总训练、饮食、身体状态和长期计划，正在生成结构化总结。",
        )
        reply = self._generate_summary_reply(
            user_query=user_query,
            start_date=start_date,
            end_date=end_date,
            datasets=datasets,
        )
        yield self._progress(
            status="success",
            node="summary_llm",
            title="最近健康总结已完成",
            detail="已生成包含身体状态、饮食状态和训练状态的总结。",
        )
        yield {
            "kind": "result",
            "result": RecentHealthSummaryResult(
                handled=True,
                action="summarized",
                reply=reply,
                payload={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    **datasets,
                },
            ),
        }

    def _collect_context_stream(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Iterator[dict[str, Any]]:
        tasks = {
            "workout_records": self._query_workout_records,
            "nutrition_records": self._query_nutrition_records,
            "body_status_records": self._query_body_status_records,
            "workout_plans": self._query_workout_plans,
            "latest_workout_plan": self._query_latest_workout_plan,
        }
        labels = {
            "workout_records": "训练数据",
            "nutrition_records": "饮食数据",
            "body_status_records": "身体状态数据",
            "workout_plans": "长期训练计划",
            "latest_workout_plan": "最新训练计划",
        }
        datasets: dict[str, Any] = {
            "workout_records": [],
            "nutrition_records": [],
            "body_status_records": [],
            "workout_plans": [],
            "latest_workout_plan": None,
        }

        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="fitmind-summary") as executor:
            future_map = {
                executor.submit(fn, user_id=user_id, start_date=start_date, end_date=end_date): key
                for key, fn in tasks.items()
            }
            for future in as_completed(future_map):
                key = future_map[future]
                label = labels[key]
                try:
                    datasets[key] = future.result()
                    if isinstance(datasets[key], list):
                        count_text = f"共 {len(datasets[key])} 条记录"
                    else:
                        count_text = "已找到 1 条记录" if datasets[key] else "未找到记录"
                    yield self._progress(
                        status="success",
                        node=f"query_{key}",
                        title=f"已查询到您的{label}",
                        detail=f"{label}查询完成，{count_text}。",
                    )
                except Exception as exc:  # noqa: BLE001 - keep the summary workflow resilient.
                    datasets[key] = []
                    yield self._progress(
                        status="error",
                        node=f"query_{key}",
                        title=f"{label}查询失败",
                        detail=str(exc),
                    )

        return datasets

    @staticmethod
    def _query_workout_records(*, user_id: int, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = WorkoutRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "id": record.id,
                    "record_date": record.record_date.isoformat(),
                    "session_name": record.session_name,
                    "duration_minutes": record.duration_minutes,
                    "completion_status": record.completion_status,
                    "perceived_exertion": record.perceived_exertion,
                    "energy_level": record.energy_level,
                    "mood": record.mood,
                    "raw_text": record.raw_text,
                    "items": [
                        {
                            "exercise_name": item.exercise_name,
                            "exercise_type": item.exercise_type,
                            "sets_count": item.sets_count,
                            "reps_text": item.reps_text,
                            "weight_text": item.weight_text,
                            "duration_text": item.duration_text,
                            "distance_text": item.distance_text,
                            "raw_text": item.raw_text,
                        }
                        for item in record.items
                    ],
                }
                for record in records
            ]

    @staticmethod
    def _query_nutrition_records(*, user_id: int, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = NutritionRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "id": record.id,
                    "record_date": record.record_date.isoformat(),
                    "raw_text": record.raw_text,
                    "calories_estimate": record.calories_estimate,
                    "protein_g_estimate": record.protein_g_estimate,
                    "carbs_g_estimate": record.carbs_g_estimate,
                    "fat_g_estimate": record.fat_g_estimate,
                }
                for record in records
            ]

    @staticmethod
    def _query_body_status_records(*, user_id: int, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = BodyStatusRecordRepository(session).list_between_dates(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "id": record.id,
                    "record_date": record.record_date.isoformat(),
                    "sleep_hours": record.sleep_hours,
                    "fatigue_level": record.fatigue_level,
                    "stress_level": record.stress_level,
                    "soreness_level": record.soreness_level,
                    "body_weight_kg": record.body_weight_kg,
                    "mood": record.mood,
                    "raw_text": record.raw_text,
                }
                for record in records
            ]

    @staticmethod
    def _query_workout_plans(*, user_id: int, start_date: date, end_date: date) -> list[dict[str, Any]]:
        del start_date, end_date
        with SessionLocal() as session:
            plans = WorkoutPlanRepository(session).list_active_plans(user_id=user_id)
            return [
                {
                    "id": plan.id,
                    "title": plan.title,
                    "plan_date": plan.plan_date.isoformat() if plan.plan_date else None,
                    "raw_text": plan.raw_text,
                    "source": plan.source,
                    "status": plan.status,
                }
                for plan in plans
            ]

    @staticmethod
    def _query_latest_workout_plan(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any] | None:
        del start_date, end_date
        with SessionLocal() as session:
            plan = WorkoutPlanRepository(session).get_latest_plan(user_id=user_id)
            if plan is None:
                return None
            return {
                "id": plan.id,
                "title": plan.title,
                "plan_date": plan.plan_date.isoformat() if plan.plan_date else None,
                "raw_text": plan.raw_text,
                "source": plan.source,
                "status": plan.status,
            }

    def _generate_summary_reply(
        self,
        *,
        user_query: str,
        start_date: date,
        end_date: date,
        datasets: dict[str, Any],
    ) -> str:
        system_prompt = self.prompt_loader.load("recent_health_summary/system.txt")
        user_prompt = self.prompt_loader.render(
            "recent_health_summary/user.txt",
            user_query=user_query,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            workout_plans=self._json_dumps(datasets.get("workout_plans", [])),
            latest_workout_plan=self._json_dumps(datasets.get("latest_workout_plan")),
            workout_records=self._json_dumps(datasets.get("workout_records", [])),
            nutrition_records=self._json_dumps(datasets.get("nutrition_records", [])),
            body_status_records=self._json_dumps(datasets.get("body_status_records", [])),
        )
        with TokenUsageTracker.scoped(workflow="recent_health_summary", node_name="summary_llm"):
            return self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
            )

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str, indent=2)

    @staticmethod
    def _progress(
        *,
        status: str,
        node: str,
        title: str,
        detail: str,
    ) -> dict[str, Any]:
        return {
            "kind": "progress",
            "event": {
                "workflow": "recent_health_summary",
                "status": status,
                "node": node,
                "title": title,
                "detail": detail,
            },
        }
