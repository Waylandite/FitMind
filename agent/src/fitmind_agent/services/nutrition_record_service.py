from __future__ import annotations

import json
import re
from datetime import date

from sqlalchemy.orm import Session

from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.schemas.intent import IntentRecognitionResult
from fitmind_agent.schemas.nutrition import NutritionSleepPersistResult
from fitmind_agent.schemas.nutrition import NutritionSleepRecordPayload
from fitmind_agent.schemas.nutrition import NutritionSleepWorkflowResult
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.nutrition_react_tools import NutritionReActToolContextBuilder
from fitmind_agent.services.prompt_loader import PromptLoader


class NutritionRecordService:
    def __init__(
        self,
        db: Session,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
        tool_context_builder: NutritionReActToolContextBuilder | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.nutrition_repo = NutritionRecordRepository(db)
        self.tool_context_builder = tool_context_builder or NutritionReActToolContextBuilder()

    def maybe_handle(
        self,
        *,
        user_id: int | None,
        user_query: str,
        intent_result: IntentRecognitionResult,
    ) -> NutritionSleepWorkflowResult:
        if user_id is None or intent_result.intent != "today_nutrition_record":
            return NutritionSleepWorkflowResult(handled=False, action="ignored", reply="")

        payload = self._extract_payload(user_id=user_id, user_query=user_query)
        persist_result = self._persist_payload(user_id=user_id, payload=payload)

        if not persist_result.saved_nutrition:
            return NutritionSleepWorkflowResult(
                handled=True,
                action="recorded",
                reply="我识别到你想记录饮食，但这句话里没有足够可落库的饮食信息。你可以补充吃了什么、份量或营养估算。",
                payload=payload,
                persist_result=persist_result,
            )

        return NutritionSleepWorkflowResult(
            handled=True,
            action="recorded",
            reply=self._build_persisted_reply(payload, persist_result),
            payload=payload,
            persist_result=persist_result,
        )

    def _extract_payload(self, *, user_id: int, user_query: str) -> NutritionSleepRecordPayload:
        current_date = date.today()
        daily_context = self._build_daily_context(user_id=user_id, record_date=current_date)
        tool_context = self.tool_context_builder.build_context(
            user_query=user_query,
            daily_context=daily_context,
        )
        system_prompt = self.prompt_loader.load("nutrition_record_extraction/system.txt")
        user_prompt = self.prompt_loader.render(
            "nutrition_record_extraction/user.txt",
            current_date=current_date.isoformat(),
            daily_context=json.dumps(daily_context, ensure_ascii=False, default=str),
            nutrition_tool_context=json.dumps(tool_context, ensure_ascii=False, default=str),
            user_query=user_query,
        )
        raw_content = self.llm_service.generate_text(
            user_text=user_prompt,
            system_prompt=system_prompt,
            temperature=0.0,
        )
        parsed = self._parse_json_object(raw_content)
        return NutritionSleepRecordPayload.model_validate(parsed)

    def _build_daily_context(self, *, user_id: int, record_date: date) -> dict:
        nutrition_record = self.nutrition_repo.get_by_user_date(
            user_id=user_id,
            record_date=record_date,
        )
        return {
            "record_date": record_date.isoformat(),
            "nutrition": (
                {
                    "raw_text": nutrition_record.raw_text,
                    "calories_estimate": nutrition_record.calories_estimate,
                    "protein_g_estimate": nutrition_record.protein_g_estimate,
                    "carbs_g_estimate": nutrition_record.carbs_g_estimate,
                    "fat_g_estimate": nutrition_record.fat_g_estimate,
                }
                if nutrition_record
                else None
            ),
        }

    def _persist_payload(
        self,
        *,
        user_id: int,
        payload: NutritionSleepRecordPayload,
    ) -> NutritionSleepPersistResult:
        nutrition_record_id: int | None = None
        if payload.nutrition.has_content and self._has_text(payload.nutrition.raw_text):
            nutrition_record = self.nutrition_repo.upsert_daily_record(
                user_id=user_id,
                record_date=payload.record_date,
                raw_text=payload.nutrition.raw_text or "",
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
        )

    @staticmethod
    def _build_persisted_reply(
        payload: NutritionSleepRecordPayload,
        result: NutritionSleepPersistResult,
    ) -> str:
        lines = [f"已保存 {result.record_date.isoformat()} 的饮食记录："]
        nutrition = payload.nutrition
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
            lines.append(f"- 今日累计：{'，'.join(parts)}")
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
            raise ValueError("No JSON object found in nutrition extraction response.")
        return json.loads(match.group(0))
