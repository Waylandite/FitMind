from __future__ import annotations

import json
import re
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.repositories.nutrition import BodyStatusRecordDraftRepository
from fitmind_agent.repositories.nutrition import BodyStatusRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.nutrition import NutritionSleepPersistResult
from fitmind_agent.schemas.nutrition import NutritionSleepRecordPayload
from fitmind_agent.schemas.nutrition import NutritionSleepWorkflowResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


CONFIRM_KEYWORDS = ("确认", "可以", "没问题", "保存", "落库", "对的", "没错", "好的")
CANCEL_KEYWORDS = ("取消", "不要", "作废", "先不", "不保存", "放弃")
QUESTION_KEYWORDS = ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")


class BodyStatusRecordService:
    def __init__(
        self,
        db: Session,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.draft_repo = BodyStatusRecordDraftRepository(db)
        self.body_status_repo = BodyStatusRecordRepository(db)

    def maybe_handle(
        self,
        *,
        user_id: int | None,
        session_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> NutritionSleepWorkflowResult:
        if user_id is None:
            return NutritionSleepWorkflowResult(handled=False, action="ignored", reply="")

        pending_draft = self.draft_repo.get_latest_pending(user_id=user_id, session_id=session_id)
        if pending_draft is not None:
            return self._handle_pending_draft(pending_draft=pending_draft, user_query=user_query)

        if intent_result.intent != "today_body_status_record":
            return NutritionSleepWorkflowResult(handled=False, action="ignored", reply="")

        payload = self._extract_payload(user_id=user_id, user_query=user_query)
        if not payload.body_status.has_content or not self._has_text(payload.body_status.raw_text):
            return NutritionSleepWorkflowResult(
                handled=True,
                action="draft_created",
                reply="我识别到你想记录身体状态，但这句话里没有足够可落库的信息。你可以补充睡眠、疲劳、酸痛、体重或心情。",
                payload=payload,
            )

        draft = self.draft_repo.create(
            {
                "user_id": user_id,
                "session_id": session_id,
                "status": "pending",
                "raw_text": user_query,
                "draft_payload": payload.model_dump(mode="json"),
                "confidence_score": Decimal(str(payload.confidence)),
            }
        )
        return NutritionSleepWorkflowResult(
            handled=True,
            action="draft_created",
            reply=self._build_confirmation_reply(payload),
            draft_id=draft.id,
            payload=payload,
        )

    def _handle_pending_draft(self, *, pending_draft, user_query: str) -> NutritionSleepWorkflowResult:
        normalized = user_query.strip().lower()

        if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
            self.draft_repo.update(pending_draft, {"status": "cancelled", "remark": user_query})
            return NutritionSleepWorkflowResult(
                handled=True,
                action="cancelled",
                reply="已取消这条身体状态草稿，没有写入数据库。",
                draft_id=pending_draft.id,
            )

        if any(keyword in normalized for keyword in CONFIRM_KEYWORDS):
            payload = NutritionSleepRecordPayload.model_validate(pending_draft.draft_payload)
            persist_result = self._persist_payload(user_id=pending_draft.user_id, payload=payload)
            self.draft_repo.update(
                pending_draft,
                {
                    "status": "confirmed",
                    "confirmed_at": datetime.now(),
                    "body_status_record_id": persist_result.body_status_record_id,
                },
            )
            return NutritionSleepWorkflowResult(
                handled=True,
                action="confirmed",
                reply=self._build_persisted_reply(payload, persist_result),
                draft_id=pending_draft.id,
                payload=payload,
                persist_result=persist_result,
            )

        if any(keyword in normalized for keyword in QUESTION_KEYWORDS):
            payload = NutritionSleepRecordPayload.model_validate(pending_draft.draft_payload)
            return NutritionSleepWorkflowResult(
                handled=True,
                action="draft_updated",
                reply=self._build_question_reply(payload),
                draft_id=pending_draft.id,
                payload=payload,
            )

        combined_query = f"{pending_draft.raw_text}\n{user_query}"
        payload = self._extract_payload(user_id=pending_draft.user_id, user_query=combined_query)
        self.draft_repo.update(
            pending_draft,
            {
                "raw_text": combined_query,
                "draft_payload": payload.model_dump(mode="json"),
                "confidence_score": Decimal(str(payload.confidence)),
            },
        )
        return NutritionSleepWorkflowResult(
            handled=True,
            action="draft_updated",
            reply=self._build_confirmation_reply(payload),
            draft_id=pending_draft.id,
            payload=payload,
        )

    def _extract_payload(self, *, user_id: int, user_query: str) -> NutritionSleepRecordPayload:
        current_date = date.today()
        daily_context = self._build_daily_context(user_id=user_id, record_date=current_date)
        system_prompt = self.prompt_loader.load("body_status_record_extraction/system.txt")
        user_prompt = self.prompt_loader.render(
            "body_status_record_extraction/user.txt",
            current_date=current_date.isoformat(),
            daily_context=json.dumps(daily_context, ensure_ascii=False, default=str),
            user_query=user_query,
        )
        with TokenUsageTracker.scoped(workflow="body_status_record", node_name="body_status_extraction"):
            raw_content = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        parsed = self._parse_json_object(raw_content)
        return NutritionSleepRecordPayload.model_validate(parsed)

    def _build_daily_context(self, *, user_id: int, record_date: date) -> dict:
        body_status_record = self.body_status_repo.get_by_user_date(
            user_id=user_id,
            record_date=record_date,
        )
        return {
            "record_date": record_date.isoformat(),
            "body_status": (
                {
                    "raw_text": body_status_record.raw_text,
                    "sleep_hours": body_status_record.sleep_hours,
                    "fatigue_level": body_status_record.fatigue_level,
                    "stress_level": body_status_record.stress_level,
                    "soreness_level": body_status_record.soreness_level,
                    "body_weight_kg": body_status_record.body_weight_kg,
                    "mood": body_status_record.mood,
                }
                if body_status_record
                else None
            ),
        }

    def _persist_payload(
        self,
        *,
        user_id: int,
        payload: NutritionSleepRecordPayload,
    ) -> NutritionSleepPersistResult:
        body_status_record_id: int | None = None
        if payload.body_status.has_content and self._has_text(payload.body_status.raw_text):
            body_status_record = self.body_status_repo.upsert_daily_record(
                user_id=user_id,
                record_date=payload.record_date,
                raw_text=payload.body_status.raw_text or "",
                sleep_hours=payload.body_status.sleep_hours,
                fatigue_level=payload.body_status.fatigue_level,
                stress_level=payload.body_status.stress_level,
                soreness_level=payload.body_status.soreness_level,
                body_weight_kg=payload.body_status.body_weight_kg,
                mood=payload.body_status.mood,
            )
            body_status_record_id = body_status_record.id

        return NutritionSleepPersistResult(
            record_date=payload.record_date,
            body_status_record_id=body_status_record_id,
            saved_body_status=body_status_record_id is not None,
        )

    @staticmethod
    def _build_confirmation_reply(payload: NutritionSleepRecordPayload) -> str:
        lines = ["我整理出这条身体状态记录，先请你确认：", ""]
        body = payload.body_status
        parts = []
        if body.sleep_hours is not None:
            parts.append(f"睡眠 {body.sleep_hours} 小时")
        if body.fatigue_level is not None:
            parts.append(f"疲劳 {body.fatigue_level}/10")
        if body.stress_level is not None:
            parts.append(f"压力 {body.stress_level}/10")
        if body.soreness_level is not None:
            parts.append(f"酸痛 {body.soreness_level}/10")
        if body.body_weight_kg is not None:
            parts.append(f"体重 {body.body_weight_kg} kg")
        if body.mood:
            parts.append(f"情绪：{body.mood}")
        if parts:
            lines.append(f"- 最新状态：{'，'.join(parts)}")
        lines.append(f"- 原文：{body.raw_text}")
        if payload.missing_fields:
            lines.append(f"- 可能还缺：{'、'.join(payload.missing_fields)}")
        lines.append("")
        lines.append("如果无误，请回复“确认保存”。如果需要修改，直接告诉我要改哪里。")
        return "\n".join(lines)

    @staticmethod
    def _build_question_reply(payload: NutritionSleepRecordPayload) -> str:
        return "\n".join(
            [
                "这条身体状态草稿还没有写入数据库，我会等你确认后再保存。",
                "",
                payload.summary_text or "当前已经生成了一条身体状态草稿。",
                "",
                "你可以回复“确认保存”，也可以继续补充睡眠、体重、疲劳、酸痛或心情。",
            ]
        )

    @staticmethod
    def _build_persisted_reply(
        payload: NutritionSleepRecordPayload,
        result: NutritionSleepPersistResult,
    ) -> str:
        lines = [f"已保存 {result.record_date.isoformat()} 的身体状态记录："]
        body = payload.body_status
        parts = []
        if body.sleep_hours is not None:
            parts.append(f"睡眠 {body.sleep_hours} 小时")
        if body.fatigue_level is not None:
            parts.append(f"疲劳 {body.fatigue_level}/10")
        if body.stress_level is not None:
            parts.append(f"压力 {body.stress_level}/10")
        if body.soreness_level is not None:
            parts.append(f"酸痛 {body.soreness_level}/10")
        if body.body_weight_kg is not None:
            parts.append(f"体重 {body.body_weight_kg} kg")
        if body.mood:
            parts.append(f"情绪：{body.mood}")
        if parts:
            lines.append(f"- 最新状态：{'，'.join(parts)}")
        if payload.missing_fields:
            lines.append(f"- 可后续补充：{'、'.join(payload.missing_fields)}")
        return "\n".join(lines)

    @staticmethod
    def _has_text(value: str | None) -> bool:
        return bool((value or "").strip())

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()

        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise ValueError("No JSON object found in body status extraction response.")
        return json.loads(match.group(0))
