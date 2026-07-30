from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from math import ceil
from typing import Any

from sqlalchemy.orm import Session

from fitmind_agent.db.session import SessionLocal
from fitmind_agent.domain.workout_taxonomy import MUSCLE_GROUP_LABELS
from fitmind_agent.domain.workout_taxonomy import resolve_muscle_groups
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.workout_history import MuscleGroup
from fitmind_agent.schemas.workout_history import WorkoutHistoryFilters
from fitmind_agent.schemas.workout_history import WorkoutHistoryPagination
from fitmind_agent.schemas.workout_history import WorkoutHistoryParsePayload
from fitmind_agent.schemas.workout_history import WorkoutHistoryResponse
from fitmind_agent.schemas.workout_history import WorkoutHistorySummary
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


MAX_LOOKBACK_DAYS = 90
DEFAULT_LOOKBACK_DAYS = 7

class WorkoutHistoryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class WorkoutHistoryQueryResult:
    handled: bool
    action: str
    reply: str
    payload: dict[str, Any] | None = None


class WorkoutHistoryService:
    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()

    def stream_maybe_handle(
        self,
        *,
        user_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
        db: Session | None = None,
    ) -> Iterator[dict[str, Any]]:
        if user_id is None or intent_result.intent != "workout_history_query":
            yield {"kind": "result", "result": WorkoutHistoryQueryResult(False, "ignored", "")}
            return

        yield self._progress(
            status="queue",
            node="history_query_start",
            title="训练日志查询模块已接管",
            detail="正在理解查询范围、训练部位和动作条件。",
        )
        yield self._progress(
            status="thinking",
            node="parse_history_filters",
            title="正在解析训练查询条件",
            detail="将自然语言转换为安全的日期、部位和动作筛选条件。",
        )
        try:
            filters = self.parse_query_filters(user_query)
        except WorkoutHistoryValidationError as exc:
            reply = f"## 查询范围\n\n无法执行本次训练记录查询：{exc}"
            yield self._progress(
                status="error",
                node="parse_history_filters",
                title="训练查询条件无效",
                detail=str(exc),
            )
            yield {
                "kind": "result",
                "result": WorkoutHistoryQueryResult(True, "invalid_filters", reply),
            }
            return

        yield self._progress(
            status="success",
            node="parse_history_filters",
            title="训练查询条件已确定",
            detail=self._describe_filters(filters),
        )
        yield self._progress(
            status="thinking",
            node="query_workout_records",
            title="正在查询训练日志",
            detail="正在读取该时间范围内已确认保存的训练记录与动作明细。",
        )
        response = self.query_history(user_id=user_id, filters=filters, db=db)
        yield self._progress(
            status="success",
            node="query_workout_records",
            title="训练日志查询完成",
            detail=f"找到 {response.pagination.total_records} 条符合条件的训练记录。",
        )
        yield self._progress(
            status="success",
            node="filter_by_muscle_group",
            title="训练部位筛选完成",
            detail=self._filter_detail(filters, response.pagination.total_records),
        )
        reply = self.format_markdown(response)
        yield self._progress(
            status="success",
            node="history_complete",
            title="训练回顾已生成",
            detail="已按日期整理训练记录和确定性统计。",
        )
        yield {
            "kind": "result",
            "result": WorkoutHistoryQueryResult(
                handled=True,
                action="queried",
                reply=reply,
                payload=response.model_dump(mode="json"),
            ),
        }

    def parse_query_filters(self, user_query: str) -> WorkoutHistoryFilters:
        today = date.today()
        default_start = today - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)
        system_prompt = self.prompt_loader.render(
            "workout_history_query/system.txt",
            current_date=today.isoformat(),
        )
        user_prompt = self.prompt_loader.render(
            "workout_history_query/user.txt",
            current_date=today.isoformat(),
            default_start_date=default_start.isoformat(),
            default_end_date=today.isoformat(),
            user_query=user_query,
        )
        try:
            with TokenUsageTracker.scoped(
                workflow="workout_history_query",
                node_name="parse_history_filters",
            ):
                raw_content = self.llm_service.generate_text(
                    user_text=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.0,
                )
            payload = WorkoutHistoryParsePayload.model_validate(self._parse_json_object(raw_content))
        except (Exception,):  # noqa: BLE001 - query parsing falls back to a safe default window.
            payload = WorkoutHistoryParsePayload()

        return self.build_filters(
            start_date=payload.start_date,
            end_date=payload.end_date,
            muscle_group=payload.muscle_group,
            exercise_keyword=payload.exercise_keyword,
        )

    @staticmethod
    def build_filters(
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        muscle_group: MuscleGroup | None = None,
        exercise_keyword: str | None = None,
    ) -> WorkoutHistoryFilters:
        today = date.today()
        end = end_date or today
        start = start_date or end - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)
        if end > today:
            raise WorkoutHistoryValidationError("暂不支持查询未来日期的训练记录。")
        if start > end:
            raise WorkoutHistoryValidationError("开始日期不能晚于结束日期。")
        if (end - start).days + 1 > MAX_LOOKBACK_DAYS:
            raise WorkoutHistoryValidationError(f"单次最多查询最近 {MAX_LOOKBACK_DAYS} 天的训练记录。")

        keyword = str(exercise_keyword or "").strip() or None
        return WorkoutHistoryFilters(
            start_date=start,
            end_date=end,
            muscle_group=muscle_group,
            exercise_keyword=keyword,
        )

    def query_history(
        self,
        *,
        user_id: int,
        filters: WorkoutHistoryFilters,
        page: int = 1,
        page_size: int = 20,
        db: Session | None = None,
    ) -> WorkoutHistoryResponse:
        if page < 1:
            raise WorkoutHistoryValidationError("页码必须从 1 开始。")
        if page_size < 1 or page_size > 50:
            raise WorkoutHistoryValidationError("每页记录数必须在 1 到 50 之间。")

        if db is None:
            with SessionLocal() as session:
                records = WorkoutRecordRepository(session).list_between_dates(
                    user_id=user_id,
                    start_date=filters.start_date,
                    end_date=filters.end_date,
                )
                return self._build_response(records, filters, page, page_size)

        records = WorkoutRecordRepository(db).list_between_dates(
            user_id=user_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
        )
        return self._build_response(records, filters, page, page_size)

    def _build_response(
        self,
        records: list[Any],
        filters: WorkoutHistoryFilters,
        page: int,
        page_size: int,
    ) -> WorkoutHistoryResponse:
        filtered_records = []
        for record in records:
            serialized = self._serialize_record(record, filters)
            if serialized is not None:
                filtered_records.append(serialized)

        filtered_records.sort(key=lambda item: (item["record_date"], item["id"]), reverse=True)
        total_records = len(filtered_records)
        total_pages = max(1, ceil(total_records / page_size))
        start_index = (page - 1) * page_size
        paged_records = filtered_records[start_index : start_index + page_size]
        summary = self._summarize(filtered_records)
        return WorkoutHistoryResponse(
            filters=filters,
            summary=summary,
            records=paged_records,
            pagination=WorkoutHistoryPagination(
                page=page,
                page_size=page_size,
                total_records=total_records,
                total_pages=total_pages,
            ),
        )

    def _serialize_record(self, record: Any, filters: WorkoutHistoryFilters) -> dict[str, Any] | None:
        record_text = " ".join(
            value for value in (record.session_name, record.raw_text) if isinstance(value, str)
        )
        record_groups = resolve_muscle_groups(record_text)
        matching_items = []
        for item in record.items:
            item_text = " ".join(
                value for value in (item.exercise_name, item.raw_text) if isinstance(value, str)
            )
            item_groups = resolve_muscle_groups(item_text, exercise_type=item.exercise_type)
            matches_keyword = self._matches_keyword(item_text, filters.exercise_keyword)
            matches_group = not filters.muscle_group or filters.muscle_group in item_groups
            if matches_keyword and matches_group:
                matching_items.append(
                    {
                        "exercise_name": item.exercise_name,
                        "exercise_type": item.exercise_type,
                        "sets_count": item.sets_count,
                        "reps_text": item.reps_text,
                        "weight_text": item.weight_text,
                        "duration_text": item.duration_text,
                        "distance_text": item.distance_text,
                        "raw_text": item.raw_text,
                        "muscle_groups": item_groups,
                    }
                )

        record_matches_keyword = self._matches_keyword(record_text, filters.exercise_keyword)
        record_matches_group = not filters.muscle_group or filters.muscle_group in record_groups
        has_item_filters = filters.muscle_group is not None or filters.exercise_keyword is not None
        if has_item_filters and not matching_items and not (record_matches_keyword and record_matches_group):
            return None

        if not has_item_filters:
            matching_items = [
                {
                    "exercise_name": item.exercise_name,
                    "exercise_type": item.exercise_type,
                    "sets_count": item.sets_count,
                    "reps_text": item.reps_text,
                    "weight_text": item.weight_text,
                    "duration_text": item.duration_text,
                    "distance_text": item.distance_text,
                    "raw_text": item.raw_text,
                    "muscle_groups": resolve_muscle_groups(
                        " ".join(
                            value
                            for value in (item.exercise_name, item.raw_text)
                            if isinstance(value, str)
                        ),
                        exercise_type=item.exercise_type,
                    ),
                }
                for item in record.items
            ]

        return {
            "id": record.id,
            "record_date": record.record_date,
            "session_name": record.session_name,
            "duration_minutes": record.duration_minutes,
            "completion_status": record.completion_status,
            "perceived_exertion": record.perceived_exertion,
            "energy_level": record.energy_level,
            "mood": record.mood,
            "raw_text": record.raw_text,
            "items": matching_items,
        }

    @staticmethod
    def _matches_keyword(text: str, keyword: str | None) -> bool:
        return not keyword or keyword.lower() in text.lower()

    @staticmethod
    def _summarize(records: list[dict[str, Any]]) -> WorkoutHistorySummary:
        durations = [record["duration_minutes"] for record in records if record["duration_minutes"] is not None]
        items = [item for record in records for item in record["items"]]
        return WorkoutHistorySummary(
            record_count=len(records),
            training_day_count=len({record["record_date"] for record in records}),
            completed_record_count=sum(record["completion_status"] == "completed" for record in records),
            total_duration_minutes=sum(durations) if durations else None,
            strength_sets_count=sum(
                item["sets_count"] or 0 for item in items if item["exercise_type"] == "strength"
            ),
            cardio_item_count=sum(item["exercise_type"] == "cardio" for item in items),
        )

    def format_markdown(self, response: WorkoutHistoryResponse) -> str:
        filters = response.filters
        summary = response.summary
        lines = [
            "## 查询范围",
            "",
            f"- {filters.start_date.isoformat()} 至 {filters.end_date.isoformat()}",
            f"- {self._filter_detail(filters, response.pagination.total_records)}",
            "",
            "## 训练概览",
            "",
            f"- 训练记录：{summary.record_count} 次，覆盖 {summary.training_day_count} 天",
            f"- 已完成：{summary.completed_record_count} 次",
            f"- 已知总时长：{summary.total_duration_minutes} 分钟" if summary.total_duration_minutes is not None else "- 已知总时长：未记录",
            f"- 力量训练组数：{summary.strength_sets_count} 组；有氧动作：{summary.cardio_item_count} 项",
            "",
            "## 训练记录",
            "",
        ]
        if not response.records:
            lines.append("该范围内没有符合条件的训练记录。")
        else:
            for record in response.records:
                title = record.session_name or "未命名训练"
                lines.append(f"### {record.record_date.isoformat()} · {title}")
                metadata = [self._completion_label(record.completion_status)]
                if record.duration_minutes is not None:
                    metadata.append(f"{record.duration_minutes} 分钟")
                if record.perceived_exertion is not None:
                    metadata.append(f"RPE {record.perceived_exertion}")
                lines.append(f"- {' · '.join(metadata)}")
                if record.items:
                    for item in record.items:
                        detail = self._format_item_detail(item)
                        lines.append(f"- {item.exercise_name}{detail}")
                else:
                    lines.append(f"- 原始记录：{record.raw_text}")
                lines.append("")
        lines.extend([
            "## 筛选说明",
            "",
            "仅展示已保存的训练记录与动作明细；统计不包含未记录的重量、时长或组数。",
        ])
        return "\n".join(lines).strip()

    @staticmethod
    def _format_item_detail(item: Any) -> str:
        parts = [
            value
            for value in (
                f"{item.sets_count} 组" if item.sets_count is not None else None,
                item.reps_text,
                item.weight_text,
                item.duration_text,
                item.distance_text,
            )
            if value
        ]
        return f"：{' · '.join(parts)}" if parts else ""

    @staticmethod
    def _completion_label(status: str) -> str:
        return {"completed": "已完成", "partial": "部分完成", "skipped": "已跳过"}.get(status, status)

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict[str, Any]:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise ValueError("No JSON object found.")
        return json.loads(match.group(0))

    @staticmethod
    def _describe_filters(filters: WorkoutHistoryFilters) -> str:
        parts = [f"{filters.start_date.isoformat()} 至 {filters.end_date.isoformat()}"]
        if filters.muscle_group:
            parts.append(f"部位：{MUSCLE_GROUP_LABELS[filters.muscle_group]}")
        if filters.exercise_keyword:
            parts.append(f"动作：{filters.exercise_keyword}")
        return "；".join(parts)

    @staticmethod
    def _filter_detail(filters: WorkoutHistoryFilters, count: int) -> str:
        parts = [f"共找到 {count} 条记录"]
        if filters.muscle_group:
            parts.append(f"部位：{MUSCLE_GROUP_LABELS[filters.muscle_group]}")
        if filters.exercise_keyword:
            parts.append(f"动作：{filters.exercise_keyword}")
        return "；".join(parts)

    @staticmethod
    def _progress(*, status: str, node: str, title: str, detail: str) -> dict[str, Any]:
        return {
            "kind": "progress",
            "event": {
                "workflow": "workout_history_query",
                "status": status,
                "node": node,
                "title": title,
                "detail": detail,
            },
        }
