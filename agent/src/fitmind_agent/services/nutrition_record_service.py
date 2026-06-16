from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.repositories.nutrition import NutritionRecordDraftRepository
from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.nutrition import NutritionSleepPersistResult
from fitmind_agent.schemas.nutrition import NutritionSleepRecordPayload
from fitmind_agent.schemas.nutrition import NutritionSleepWorkflowResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.nutrition_react_tools import NutritionLangGraphReActRunner
from fitmind_agent.services.prompt_loader import PromptLoader


CONFIRM_KEYWORDS = ("确认", "可以", "没问题", "保存", "落库", "对的", "没错", "好的")
CANCEL_KEYWORDS = ("取消", "不要", "作废", "先不", "不保存")
QUESTION_KEYWORDS = ("为什么", "怎么", "什么意思", "哪里", "吗", "？", "?")


class NutritionRecordService:
    def __init__(
        self,
        db: Session,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        react_runner: NutritionLangGraphReActRunner | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.draft_repo = NutritionRecordDraftRepository(db)
        self.nutrition_repo = NutritionRecordRepository(db)
        self.react_runner = react_runner or NutritionLangGraphReActRunner(
            llm_service=self.llm_service,
            prompt_loader=self.prompt_loader,
        )

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
            return self._handle_pending_draft(
                pending_draft=pending_draft,
                user_query=user_query,
            )

        if intent_result.intent != "today_nutrition_record":
            return NutritionSleepWorkflowResult(handled=False, action="ignored", reply="")

        payload = self._extract_payload(user_id=user_id, user_query=user_query)
        if not payload.nutrition.has_content or not self._has_text(payload.nutrition.raw_text):
            return NutritionSleepWorkflowResult(
                handled=True,
                action="draft_created",
                reply="我识别到你想记录饮食，但这句话里没有足够可落库的饮食信息。你可以补充吃了什么、份量或营养估算。",
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

    def stream_maybe_handle(
        self,
        *,
        user_id: int | None,
        session_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> Iterator[dict]:
        if user_id is None:
            yield {
                "kind": "result",
                "result": NutritionSleepWorkflowResult(handled=False, action="ignored", reply=""),
            }
            return

        pending_draft = self.draft_repo.get_latest_pending(user_id=user_id, session_id=session_id)
        if pending_draft is not None:
            yield {
                "kind": "progress",
                "event": {
                    "workflow": "nutrition_record",
                    "status": "thinking",
                    "node": "pending_draft",
                    "title": "检测到待确认饮食草稿",
                    "detail": "正在判断本轮输入是确认、取消、提问还是纠错。",
                },
            }
            yield {
                "kind": "result",
                "result": self._handle_pending_draft(
                    pending_draft=pending_draft,
                    user_query=user_query,
                ),
            }
            return

        if intent_result.intent != "today_nutrition_record":
            yield {
                "kind": "result",
                "result": NutritionSleepWorkflowResult(handled=False, action="ignored", reply=""),
            }
            return

        yield {
            "kind": "progress",
            "event": {
                "workflow": "nutrition_record",
                "status": "queue",
                "node": "nutrition_record",
                "title": "饮食记录模块已接管",
                "detail": "正在准备今日上下文和营养 ReAct 工具链。",
            },
        }
        payload = yield from self._extract_payload_stream(user_id=user_id, user_query=user_query)
        if not payload.nutrition.has_content or not self._has_text(payload.nutrition.raw_text):
            yield {
                "kind": "result",
                "result": NutritionSleepWorkflowResult(
                    handled=True,
                    action="draft_created",
                    reply="我识别到你想记录饮食，但这句话里没有足够可落库的饮食信息。你可以补充吃了什么、份量或营养估算。",
                    payload=payload,
                ),
            }
            return

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
        yield {
            "kind": "progress",
            "event": {
                "workflow": "nutrition_record",
                "status": "success",
                "node": "draft_create",
                "title": "饮食草稿已生成",
                "detail": f"草稿 #{draft.id} 已等待用户确认，暂未写入正式记录表。",
            },
        }
        yield {
            "kind": "result",
            "result": NutritionSleepWorkflowResult(
                handled=True,
                action="draft_created",
                reply=self._build_confirmation_reply(payload),
                draft_id=draft.id,
                payload=payload,
            ),
        }

    def _handle_pending_draft(self, *, pending_draft, user_query: str) -> NutritionSleepWorkflowResult:
        normalized = user_query.strip().lower()

        if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
            self.draft_repo.update(pending_draft, {"status": "cancelled"})
            return NutritionSleepWorkflowResult(
                handled=True,
                action="cancelled",
                reply="已取消这条饮食记录草稿，没有写入数据库。",
                draft_id=pending_draft.id,
            )

        if any(keyword in normalized for keyword in CONFIRM_KEYWORDS):
            payload = NutritionSleepRecordPayload.model_validate(pending_draft.draft_payload)
            persist_result = self._persist_payload(
                user_id=pending_draft.user_id,
                payload=payload,
                raw_text=pending_draft.raw_text,
            )
            self.draft_repo.update(
                pending_draft,
                {
                    "status": "confirmed",
                    "confirmed_at": datetime.now(),
                    "nutrition_record_id": persist_result.nutrition_record_id,
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
        react_result = self.react_runner.run(
            user_query=user_query,
            daily_context=daily_context,
            current_date=current_date.isoformat(),
        )

        final_payload = react_result.get("final_payload")
        return NutritionSleepRecordPayload.model_validate(final_payload)

    def _extract_payload_stream(
        self,
        *,
        user_id: int,
        user_query: str,
    ) -> Iterator[dict]:
        current_date = date.today()
        daily_context = self._build_daily_context(user_id=user_id, record_date=current_date)
        final_payload: dict | None = None
        for event in self.react_runner.stream_run(
            user_query=user_query,
            daily_context=daily_context,
            current_date=current_date.isoformat(),
        ):
            if event.get("kind") == "progress":
                yield event
            elif event.get("kind") == "final":
                result = event.get("result") or {}
                final_payload = result.get("final_payload")

        yield {
            "kind": "progress",
            "event": {
                "workflow": "nutrition_record",
                "status": "success",
                "node": "payload_validate",
                "title": "结构化饮食数据校验完成",
                "detail": "已转换为 FitMind 可确认入库的饮食记录 JSON。",
            },
        }
        return NutritionSleepRecordPayload.model_validate(final_payload)

    def _build_daily_context(self, *, user_id: int, record_date: date) -> dict:
        return {
            "record_date": record_date.isoformat(),
            "nutrition": None,
            "mode": "incremental_only",
            "instruction": "只计算本次用户输入。历史饮食记录由后端确认保存时读取数据库并累加，不要在本轮提取中复用历史 raw_text。",
        }

    def _persist_payload(
        self,
        *,
        user_id: int,
        payload: NutritionSleepRecordPayload,
        raw_text: str | None = None,
    ) -> NutritionSleepPersistResult:
        nutrition_record_id: int | None = None
        nutrition_record = None
        if payload.nutrition.has_content and self._has_text(payload.nutrition.raw_text):
            nutrition_record = self.nutrition_repo.upsert_daily_record(
                user_id=user_id,
                record_date=payload.record_date,
                raw_text=raw_text or payload.nutrition.raw_text or "",
                calories_estimate=payload.nutrition.calories_estimate,
                protein_g_estimate=payload.nutrition.protein_g_estimate,
                carbs_g_estimate=payload.nutrition.carbs_g_estimate,
                fat_g_estimate=payload.nutrition.fat_g_estimate,
            )
            nutrition_record_id = nutrition_record.id

        return NutritionSleepPersistResult(
            record_date=payload.record_date,
            nutrition_record_id=nutrition_record_id,
            saved_nutrition=nutrition_record_id is not None,
            calories_estimate=nutrition_record.calories_estimate if nutrition_record else None,
            protein_g_estimate=nutrition_record.protein_g_estimate if nutrition_record else None,
            carbs_g_estimate=nutrition_record.carbs_g_estimate if nutrition_record else None,
            fat_g_estimate=nutrition_record.fat_g_estimate if nutrition_record else None,
        )

    @staticmethod
    def _build_confirmation_reply(payload: NutritionSleepRecordPayload) -> str:
        lines = ["我根据本地营养工具算出这条饮食记录，先请你确认：", ""]
        lines.append(f"- 日期：{payload.record_date.isoformat()}")
        if payload.nutrition.items:
            lines.append("- 食物明细：")
            for index, item in enumerate(payload.nutrition.items, start=1):
                parts = [item.food_name]
                if item.amount_g is not None:
                    parts.append(f"{item.amount_g}g")
                macro_parts = []
                if item.calories_kcal is not None:
                    macro_parts.append(f"{item.calories_kcal}kcal")
                if item.protein_g is not None:
                    macro_parts.append(f"蛋白 {item.protein_g}g")
                if item.carbs_g is not None:
                    macro_parts.append(f"碳水 {item.carbs_g}g")
                if item.fat_g is not None:
                    macro_parts.append(f"脂肪 {item.fat_g}g")
                if macro_parts:
                    parts.append(" / ".join(macro_parts))
                lines.append(f"  {index}. {' - '.join(parts)}")

        total_parts = []
        nutrition = payload.nutrition
        if nutrition.calories_estimate is not None:
            total_parts.append(f"热量约 {nutrition.calories_estimate} kcal")
        if nutrition.protein_g_estimate is not None:
            total_parts.append(f"蛋白质约 {nutrition.protein_g_estimate} g")
        if nutrition.carbs_g_estimate is not None:
            total_parts.append(f"碳水约 {nutrition.carbs_g_estimate} g")
        if nutrition.fat_g_estimate is not None:
            total_parts.append(f"脂肪约 {nutrition.fat_g_estimate} g")
        if total_parts:
            lines.append(f"- 本次新增估算：{'，'.join(total_parts)}")
        if payload.missing_fields:
            lines.append(f"- 注意：{'、'.join(payload.missing_fields)}")

        lines.append("")
        lines.append("如果无误，请回复“确认保存”。如果需要修改，直接告诉我要改哪里，比如“牛肉不是一份，是200g”。")
        return "\n".join(lines)

    @staticmethod
    def _build_question_reply(payload: NutritionSleepRecordPayload) -> str:
        lines = [
            "这条饮食草稿还没有写入数据库，我会等你确认后再保存。",
            "",
            payload.summary_text or "当前已经生成了一条饮食记录草稿。",
            "",
            "你可以回复“确认保存”，也可以直接告诉我要修改的食物、份量或营养信息。",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_persisted_reply(
        payload: NutritionSleepRecordPayload,
        result: NutritionSleepPersistResult,
    ) -> str:
        lines = [f"已保存 {result.record_date.isoformat()} 的饮食记录："]
        nutrition = result
        parts = []
        if nutrition.calories_estimate is not None:
            parts.append(f"热量约 {nutrition.calories_estimate} kcal")
        if nutrition.protein_g_estimate is not None:
            parts.append(f"蛋白质约 {nutrition.protein_g_estimate} g")
        if nutrition.carbs_g_estimate is not None:
            parts.append(f"碳水约 {nutrition.carbs_g_estimate} g")
        if nutrition.fat_g_estimate is not None:
            parts.append(f"脂肪约 {nutrition.fat_g_estimate} g")
        if parts:
            lines.append(f"- 保存后今日累计：{'，'.join(parts)}")
        if payload.missing_fields:
            lines.append(f"- 可后续补充：{'、'.join(payload.missing_fields)}")
        return "\n".join(lines)

    @staticmethod
    def _has_text(value: str | None) -> bool:
        return bool((value or "").strip())
