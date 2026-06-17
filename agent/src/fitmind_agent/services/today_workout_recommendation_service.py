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
from fitmind_agent.repositories.workout import WorkoutPlanRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


@dataclass(frozen=True)
class TodayWorkoutRecommendationResult:
    handled: bool
    action: str
    reply: str
    payload: dict[str, Any] | None = None


class TodayWorkoutRecommendationService:
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
        if user_id is None or intent_result.intent != "today_workout_recommendation":
            yield {
                "kind": "result",
                "result": TodayWorkoutRecommendationResult(
                    handled=False,
                    action="ignored",
                    reply="",
                ),
            }
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days - 1)
        yield self._progress(
            status="queue",
            node="recommendation_start",
            title="今日训练推荐模块已接管",
            detail=f"准备查询 {start_date.isoformat()} 至 {end_date.isoformat()} 的训练记录，并读取最新长期训练计划。",
        )

        datasets = yield from self._collect_context_stream(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        yield self._progress(
            status="thinking",
            node="recommendation_llm",
            title="正在生成今日训练建议",
            detail="已汇总最新长期训练计划与最近 7 天训练记录，正在结合训练恢复与安排逻辑生成推荐。",
        )
        reply = self._generate_recommendation_reply(
            user_query=user_query,
            current_date=end_date,
            start_date=start_date,
            end_date=end_date,
            datasets=datasets,
        )
        yield self._progress(
            status="success",
            node="recommendation_llm",
            title="今日训练推荐已完成",
            detail="已生成可直接阅读的今日训练建议与训练单。",
        )
        yield {
            "kind": "result",
            "result": TodayWorkoutRecommendationResult(
                handled=True,
                action="recommended",
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
            "latest_workout_plan": self._query_latest_workout_plan,
            "recent_workout_records": self._query_recent_workout_records,
        }
        labels = {
            "latest_workout_plan": "最新长期训练计划",
            "recent_workout_records": "最近 7 天训练记录",
        }
        datasets: dict[str, Any] = {
            "latest_workout_plan": None,
            "recent_workout_records": [],
        }

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="fitmind-workout-reco") as executor:
            future_map = {
                executor.submit(fn, user_id=user_id, start_date=start_date, end_date=end_date): key
                for key, fn in tasks.items()
            }
            for future in as_completed(future_map):
                key = future_map[future]
                label = labels[key]
                try:
                    datasets[key] = future.result()
                    if key == "latest_workout_plan":
                        count_text = "已找到 1 条记录" if datasets[key] else "未找到记录"
                    else:
                        count_text = f"共 {len(datasets[key])} 条记录"
                    yield self._progress(
                        status="success",
                        node=f"query_{key}",
                        title=f"已查询到您的{label}",
                        detail=f"{label}查询完成，{count_text}。",
                    )
                except Exception as exc:  # noqa: BLE001 - keep recommendation workflow resilient.
                    datasets[key] = None if key == "latest_workout_plan" else []
                    yield self._progress(
                        status="error",
                        node=f"query_{key}",
                        title=f"{label}查询失败",
                        detail=str(exc),
                    )

        return datasets

    @staticmethod
    def _query_latest_workout_plan(*, user_id: int, start_date: date, end_date: date) -> dict[str, Any] | None:
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
                "remark": plan.remark,
            }

    @staticmethod
    def _query_recent_workout_records(*, user_id: int, start_date: date, end_date: date) -> list[dict[str, Any]]:
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

    def _generate_recommendation_reply(
        self,
        *,
        user_query: str,
        current_date: date,
        start_date: date,
        end_date: date,
        datasets: dict[str, Any],
    ) -> str:
        system_prompt = self.prompt_loader.load("today_workout_recommendation/system.txt")
        user_prompt = self.prompt_loader.render(
            "today_workout_recommendation/user.txt",
            current_date=current_date.isoformat(),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            user_query=user_query,
            latest_workout_plan=json.dumps(
                datasets.get("latest_workout_plan"),
                ensure_ascii=False,
                default=str,
            ),
            recent_workout_records=json.dumps(
                datasets.get("recent_workout_records", []),
                ensure_ascii=False,
                default=str,
            ),
        )
        with TokenUsageTracker.scoped(
            workflow="today_workout_recommendation",
            node_name="recommendation_llm",
        ):
            reply = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        return reply.strip()

    @staticmethod
    def _progress(*, status: str, node: str, title: str, detail: str) -> dict[str, Any]:
        return {
            "kind": "progress",
            "event": {
                "workflow": "today_workout_recommendation",
                "status": status,
                "node": node,
                "title": title,
                "detail": detail,
            },
        }
