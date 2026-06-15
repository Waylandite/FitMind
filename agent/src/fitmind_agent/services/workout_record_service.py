from __future__ import annotations

import json
import re
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.repositories.workout import WorkoutRecordDraftRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.workout import WorkoutPersistResult
from fitmind_agent.schemas.workout import WorkoutRecordDraftPayload
from fitmind_agent.schemas.workout import WorkoutRecordWorkflowResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


CONFIRM_KEYWORDS = ("确认", "可以", "没问题", "保存", "落库", "对的", "没错", "好的")
CANCEL_KEYWORDS = ("取消", "不要", "作废", "先不", "不保存")
QUESTION_KEYWORDS = ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")


class WorkoutRecordService:
    def __init__(
        self,
        db: Session,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.draft_repo = WorkoutRecordDraftRepository(db)
        self.record_repo = WorkoutRecordRepository(db)

    def maybe_handle(
        self,
        *,
        user_id: int | None,
        session_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> WorkoutRecordWorkflowResult:
        if user_id is None:
            return WorkoutRecordWorkflowResult(
                handled=False,
                action="ignored",
                reply="",
            )

        pending_draft = self.draft_repo.get_latest_pending(user_id=user_id, session_id=session_id)
        if pending_draft is not None:
            return self._handle_pending_draft(
                pending_draft=pending_draft,
                user_query=user_query,
            )

        if intent_result.intent != "today_workout_record":
            return WorkoutRecordWorkflowResult(
                handled=False,
                action="ignored",
                reply="",
            )

        draft_payload = self._extract_draft(user_query=user_query, previous_draft=None)
        draft = self.draft_repo.create(
            {
                "user_id": user_id,
                "session_id": session_id,
                "status": "pending",
                "raw_text": user_query,
                "draft_payload": draft_payload.model_dump(mode="json"),
                "confidence_score": Decimal(str(draft_payload.confidence)),
            }
        )
        return WorkoutRecordWorkflowResult(
            handled=True,
            action="draft_created",
            reply=self._build_confirmation_reply(draft_payload),
            draft_id=draft.id,
            draft_payload=draft_payload,
        )

    def _handle_pending_draft(
        self,
        *,
        pending_draft,
        user_query: str,
    ) -> WorkoutRecordWorkflowResult:
        normalized = user_query.strip().lower()

        if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
            self.draft_repo.update(pending_draft, {"status": "cancelled", "remark": user_query})
            return WorkoutRecordWorkflowResult(
                handled=True,
                action="cancelled",
                reply="已取消这条训练记录草稿，没有写入数据库。",
                draft_id=pending_draft.id,
            )

        if any(keyword in normalized for keyword in CONFIRM_KEYWORDS):
            draft_payload = WorkoutRecordDraftPayload.model_validate(pending_draft.draft_payload)
            persist_result = self._persist_draft(
                user_id=pending_draft.user_id,
                raw_text=pending_draft.raw_text,
                draft_payload=draft_payload,
            )
            self.draft_repo.update(
                pending_draft,
                {
                    "status": "confirmed",
                    "confirmed_at": datetime.now(),
                    "workout_record_id": persist_result.workout_record_id,
                },
            )
            return WorkoutRecordWorkflowResult(
                handled=True,
                action="confirmed",
                reply=self._build_persisted_reply(persist_result),
                draft_id=pending_draft.id,
                draft_payload=draft_payload,
                persist_result=persist_result,
            )

        if any(keyword in normalized for keyword in QUESTION_KEYWORDS):
            draft_payload = WorkoutRecordDraftPayload.model_validate(pending_draft.draft_payload)
            return WorkoutRecordWorkflowResult(
                handled=True,
                action="draft_updated",
                reply=self._build_question_reply(draft_payload),
                draft_id=pending_draft.id,
                draft_payload=draft_payload,
            )

        previous_payload = pending_draft.draft_payload or {}
        draft_payload = self._extract_draft(
            user_query=user_query,
            previous_draft=previous_payload,
        )
        self.draft_repo.update(
            pending_draft,
            {
                "raw_text": f"{pending_draft.raw_text}\n{user_query}",
                "draft_payload": draft_payload.model_dump(mode="json"),
                "confidence_score": Decimal(str(draft_payload.confidence)),
            },
        )
        return WorkoutRecordWorkflowResult(
            handled=True,
            action="draft_updated",
            reply=self._build_confirmation_reply(draft_payload),
            draft_id=pending_draft.id,
            draft_payload=draft_payload,
        )

    def _extract_draft(
        self,
        *,
        user_query: str,
        previous_draft: dict | None,
    ) -> WorkoutRecordDraftPayload:
        system_prompt = self.prompt_loader.load("workout_record_extraction/system.txt")
        user_prompt = self.prompt_loader.render(
            "workout_record_extraction/user.txt",
            current_date=date.today().isoformat(),
            previous_draft=json.dumps(previous_draft or {}, ensure_ascii=False),
            user_query=user_query,
        )
        with TokenUsageTracker.scoped(workflow="workout_record", node_name="workout_record_extraction"):
            raw_content = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        parsed = self._parse_json_object(raw_content)
        return WorkoutRecordDraftPayload.model_validate(parsed)

    def _persist_draft(
        self,
        *,
        user_id: int,
        raw_text: str,
        draft_payload: WorkoutRecordDraftPayload,
    ) -> WorkoutPersistResult:
        record = self.record_repo.upsert_daily_record(
            user_id=user_id,
            record_date=draft_payload.record_date,
            session_name=draft_payload.session_name,
            duration_minutes=draft_payload.duration_minutes,
            completion_status=draft_payload.completion_status,
            perceived_exertion=draft_payload.perceived_exertion,
            energy_level=draft_payload.energy_level,
            mood=draft_payload.mood,
            raw_text=raw_text,
        )
        items = [
            item.model_dump(mode="json")
            for item in draft_payload.exercises
            if item.exercise_name.strip()
        ]
        created_items = self.record_repo.replace_items(
            workout_record_id=record.id,
            items=items,
        )
        return WorkoutPersistResult(
            workout_record_id=record.id,
            item_count=len(created_items),
            record_date=draft_payload.record_date,
            session_name=draft_payload.session_name,
        )

    @staticmethod
    def _build_confirmation_reply(draft_payload: WorkoutRecordDraftPayload) -> str:
        lines = ["我提取到这条训练记录，先请你确认一下：", ""]
        lines.append(f"- 日期：{draft_payload.record_date.isoformat()}")
        if draft_payload.session_name:
            lines.append(f"- 训练：{draft_payload.session_name}")

        if draft_payload.exercises:
            lines.append("- 动作：")
            for index, item in enumerate(draft_payload.exercises, start=1):
                parts = [item.exercise_name]
                if item.sets_count is not None:
                    parts.append(f"{item.sets_count} 组")
                if item.reps_text:
                    parts.append(item.reps_text)
                if item.weight_text:
                    parts.append(item.weight_text)
                lines.append(f"  {index}. {' / '.join(parts)}")
        else:
            lines.append("- 动作：暂未提取到明确动作")

        if draft_payload.missing_fields:
            lines.append("")
            lines.append(f"可能还缺：{'、'.join(draft_payload.missing_fields)}")

        lines.append("")
        lines.append("如果无误，请回复“确认保存”。如果需要修改，直接告诉我要改哪里。")
        return "\n".join(lines)

    @staticmethod
    def _build_persisted_reply(result: WorkoutPersistResult) -> str:
        title = f"「{result.session_name}」" if result.session_name else "训练记录"
        return (
            f"已保存 {title}，日期 {result.record_date.isoformat()}，"
            f"共写入 {result.item_count} 个动作明细。"
        )

    @staticmethod
    def _build_question_reply(draft_payload: WorkoutRecordDraftPayload) -> str:
        lines = [
            "这条草稿还没有写入数据库，我会等你确认后再保存。",
            "",
            draft_payload.summary_text or "当前已经生成了一条训练记录草稿。",
        ]
        if draft_payload.missing_fields:
            lines.append("")
            lines.append(f"目前可能还缺：{'、'.join(draft_payload.missing_fields)}")
        lines.append("")
        lines.append("你可以回复“确认保存”，也可以直接告诉我要修改的动作、组数、次数或重量。")
        return "\n".join(lines)

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()

        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise ValueError("No JSON object found in workout extraction response.")

        return json.loads(match.group(0))
