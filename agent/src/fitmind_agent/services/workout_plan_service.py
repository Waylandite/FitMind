from __future__ import annotations

import json
import re
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.repositories.workout import WorkoutPlanDraftRepository
from fitmind_agent.repositories.workout import WorkoutPlanRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.plan import WorkoutPlanDraftPayload
from fitmind_agent.schemas.plan import WorkoutPlanPersistResult
from fitmind_agent.schemas.plan import WorkoutPlanWorkflowResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


CONFIRM_KEYWORDS = ("确认", "可以", "没问题", "保存", "落库", "对的", "没错", "好的")
CANCEL_KEYWORDS = ("取消", "不要", "作废", "先不", "不保存", "放弃")
QUESTION_KEYWORDS = ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")


class WorkoutPlanService:
    def __init__(
        self,
        db: Session,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.draft_repo = WorkoutPlanDraftRepository(db)
        self.plan_repo = WorkoutPlanRepository(db)

    def maybe_handle(
        self,
        *,
        user_id: int | None,
        session_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> WorkoutPlanWorkflowResult:
        if user_id is None:
            return WorkoutPlanWorkflowResult(handled=False, action="ignored", reply="")

        pending_draft = self.draft_repo.get_latest_pending(user_id=user_id, session_id=session_id)
        if pending_draft is not None:
            return self._handle_pending_draft(pending_draft=pending_draft, user_query=user_query)

        if intent_result.intent != "user_workout_plan_update":
            return WorkoutPlanWorkflowResult(handled=False, action="ignored", reply="")

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
        return WorkoutPlanWorkflowResult(
            handled=True,
            action="draft_created",
            reply=self._build_confirmation_reply(draft_payload),
            draft_id=draft.id,
            draft_payload=draft_payload,
        )

    def _handle_pending_draft(self, *, pending_draft, user_query: str) -> WorkoutPlanWorkflowResult:
        normalized = user_query.strip().lower()

        if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
            self.draft_repo.update(pending_draft, {"status": "cancelled", "remark": user_query})
            return WorkoutPlanWorkflowResult(
                handled=True,
                action="cancelled",
                reply="已取消这条长期训练计划草稿，没有写入数据库。",
                draft_id=pending_draft.id,
            )

        if any(keyword in normalized for keyword in CONFIRM_KEYWORDS):
            draft_payload = WorkoutPlanDraftPayload.model_validate(pending_draft.draft_payload)
            persist_result = self._persist_draft(
                user_id=pending_draft.user_id,
                draft_payload=draft_payload,
            )
            self.draft_repo.update(
                pending_draft,
                {
                    "status": "confirmed",
                    "confirmed_at": datetime.now(),
                    "workout_plan_id": persist_result.workout_plan_id,
                },
            )
            return WorkoutPlanWorkflowResult(
                handled=True,
                action="confirmed",
                reply=self._build_persisted_reply(persist_result),
                draft_id=pending_draft.id,
                draft_payload=draft_payload,
                persist_result=persist_result,
            )

        if any(keyword in normalized for keyword in QUESTION_KEYWORDS):
            draft_payload = WorkoutPlanDraftPayload.model_validate(pending_draft.draft_payload)
            return WorkoutPlanWorkflowResult(
                handled=True,
                action="draft_updated",
                reply=self._build_question_reply(draft_payload),
                draft_id=pending_draft.id,
                draft_payload=draft_payload,
            )

        draft_payload = self._extract_draft(
            user_query=user_query,
            previous_draft=pending_draft.draft_payload or {},
        )
        self.draft_repo.update(
            pending_draft,
            {
                "raw_text": f"{pending_draft.raw_text}\n{user_query}",
                "draft_payload": draft_payload.model_dump(mode="json"),
                "confidence_score": Decimal(str(draft_payload.confidence)),
            },
        )
        return WorkoutPlanWorkflowResult(
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
    ) -> WorkoutPlanDraftPayload:
        system_prompt = self.prompt_loader.load("workout_plan_update_extraction/system.txt")
        user_prompt = self.prompt_loader.render(
            "workout_plan_update_extraction/user.txt",
            current_date=date.today().isoformat(),
            previous_draft=json.dumps(previous_draft or {}, ensure_ascii=False, default=str),
            user_query=user_query,
        )
        with TokenUsageTracker.scoped(workflow="workout_plan_update", node_name="workout_plan_extraction"):
            raw_content = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        parsed = self._parse_json_object(raw_content)
        return WorkoutPlanDraftPayload.model_validate(parsed)

    def _persist_draft(
        self,
        *,
        user_id: int,
        draft_payload: WorkoutPlanDraftPayload,
    ) -> WorkoutPlanPersistResult:
        plan = self.plan_repo.create_plan(
            user_id=user_id,
            title=draft_payload.title,
            plan_date=draft_payload.plan_date,
            raw_text=draft_payload.raw_text,
            source=draft_payload.source,
            status=draft_payload.status,
            remark=draft_payload.remark,
        )
        return WorkoutPlanPersistResult(
            workout_plan_id=plan.id,
            title=plan.title,
            plan_date=plan.plan_date,
        )

    @staticmethod
    def _build_confirmation_reply(draft_payload: WorkoutPlanDraftPayload) -> str:
        lines = ["我整理出这条长期训练计划更新，先请你确认：", ""]
        if draft_payload.title:
            lines.append(f"- 标题：{draft_payload.title}")
        if draft_payload.plan_date:
            lines.append(f"- 日期：{draft_payload.plan_date.isoformat()}")
        lines.append(f"- 计划内容：{draft_payload.raw_text}")
        if draft_payload.remark:
            lines.append(f"- 备注：{draft_payload.remark}")
        if draft_payload.missing_fields:
            lines.append(f"- 可能还缺：{'、'.join(draft_payload.missing_fields)}")
        lines.append("")
        lines.append("如果无误，请回复“确认保存”。如果需要修改，直接告诉我要改哪里。")
        return "\n".join(lines)

    @staticmethod
    def _build_question_reply(draft_payload: WorkoutPlanDraftPayload) -> str:
        return "\n".join(
            [
                "这条长期训练计划草稿还没有写入数据库，我会等你确认后再保存。",
                "",
                draft_payload.summary_text or draft_payload.raw_text,
                "",
                "你可以回复“确认保存”，也可以继续补充训练频率、周期、目标或动作安排。",
            ]
        )

    @staticmethod
    def _build_persisted_reply(result: WorkoutPlanPersistResult) -> str:
        title = f"「{result.title}」" if result.title else "新的长期训练计划"
        return f"已保存{title}，计划 ID：{result.workout_plan_id}。"

    @staticmethod
    def _parse_json_object(raw_content: str) -> dict:
        stripped = raw_content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()

        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise ValueError("No JSON object found in workout plan update response.")
        return json.loads(match.group(0))
