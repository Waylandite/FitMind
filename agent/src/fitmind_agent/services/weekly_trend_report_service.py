from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.weekly_analytics import WeeklyAnalyticsResponse
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsQueryError
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsService


@dataclass(frozen=True)
class WeeklyTrendReportResult:
    handled: bool
    action: str
    reply: str
    payload: dict[str, Any] | None = None


class WeeklyTrendReportService:
    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        analytics_service: WeeklyAnalyticsService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.analytics_service = analytics_service or WeeklyAnalyticsService()

    def stream_maybe_handle(
        self,
        *,
        user_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> Iterator[dict[str, Any]]:
        if user_id is None or intent_result.intent != "weekly_trend_report":
            yield {
                "kind": "result",
                "result": WeeklyTrendReportResult(False, "ignored", ""),
            }
            return

        yield self._progress(
            status="queue",
            node="weekly_report_start",
            title="周报趋势模块已接管",
            detail="正在确定本周与上周同期范围，并准备查询三类健康数据。",
        )

        analytics = None
        completed_datasets = 0
        reported_error = False
        try:
            for event in self.analytics_service.stream_analyze(user_id=user_id):
                if event["kind"] == "dataset":
                    completed_datasets += 1
                    dataset = event["dataset"]
                    yield self._dataset_progress(
                        dataset=dataset,
                        status="success",
                        count=event["count"],
                    )
                    if completed_datasets == 3:
                        yield self._progress(
                            status="thinking",
                            node="aggregate_weekly_metrics",
                            title="正在计算跨周趋势",
                            detail="三类数据已就绪，正在统一计算当前周期、上期指标与每日趋势。",
                        )
                elif event["kind"] == "dataset_error":
                    reported_error = True
                    yield self._dataset_progress(
                        dataset=event["dataset"],
                        status="error",
                        detail=event["error"],
                    )
                elif event["kind"] == "result":
                    analytics = event["result"]
        except WeeklyAnalyticsQueryError as exc:
            if not reported_error:
                yield self._progress(
                    status="error",
                    node="aggregate_weekly_metrics",
                    title="周报数据查询失败",
                    detail=str(exc),
                )
            yield {
                "kind": "result",
                "result": WeeklyTrendReportResult(
                    handled=True,
                    action="query_failed",
                    reply=f"## 本周结论\n\n周报数据暂时无法读取：{exc}",
                ),
            }
            return

        if analytics is None:
            yield {
                "kind": "result",
                "result": WeeklyTrendReportResult(
                    handled=True,
                    action="query_failed",
                    reply="## 本周结论\n\n周报统计暂时没有生成结果，请稍后重试。",
                ),
            }
            return

        yield self._progress(
            status="success",
            node="aggregate_weekly_metrics",
            title="跨周指标计算完成",
            detail="已完成训练、饮食、恢复指标及每日趋势的确定性统计。",
        )
        yield self._progress(
            status="thinking",
            node="weekly_report_llm",
            title="正在解读本周表现",
            detail="模型只会分析已计算指标，不会补写数据库中不存在的事实。",
        )
        reply = self._generate_report(user_query=user_query, analytics=analytics)
        yield self._progress(
            status="success",
            node="weekly_report_llm",
            title="周报解读已生成",
            detail="已形成训练、饮食、恢复和下周行动建议。",
        )
        yield self._progress(
            status="success",
            node="weekly_report_complete",
            title="本周趋势报告已完成",
            detail="周报基于实时数据生成，本次不会保存额外报告快照。",
        )
        yield {
            "kind": "result",
            "result": WeeklyTrendReportResult(
                handled=True,
                action="reported",
                reply=reply,
                payload=analytics.model_dump(mode="json"),
            ),
        }

    def _generate_report(
        self,
        *,
        user_query: str,
        analytics: WeeklyAnalyticsResponse,
    ) -> str:
        system_prompt = self.prompt_loader.load("weekly_trend_report/system.txt")
        user_prompt = self.prompt_loader.render(
            "weekly_trend_report/user.txt",
            user_query=user_query,
            analytics_json=json.dumps(
                analytics.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
        )
        with TokenUsageTracker.scoped(
            workflow="weekly_trend_report",
            node_name="weekly_report_llm",
        ):
            return self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
            )

    @staticmethod
    def _dataset_progress(
        *,
        dataset: str,
        status: str,
        count: int | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        config = {
            "workouts": ("query_weekly_workouts", "训练数据"),
            "nutrition": ("query_weekly_nutrition", "饮食数据"),
            "body_status": ("query_weekly_body_status", "身体状态数据"),
        }
        node, label = config[dataset]
        if status == "success":
            title = f"已查询到您的{label}"
            message = f"两个对比周期共读取 {count or 0} 条{label}记录。"
        else:
            title = f"{label}查询失败"
            message = detail or "数据库查询异常。"
        return WeeklyTrendReportService._progress(
            status=status,
            node=node,
            title=title,
            detail=message,
        )

    @staticmethod
    def _progress(*, status: str, node: str, title: str, detail: str) -> dict[str, Any]:
        return {
            "kind": "progress",
            "event": {
                "workflow": "weekly_trend_report",
                "status": status,
                "node": node,
                "title": title,
                "detail": detail,
            },
        }
