from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from fitmind_agent.repositories.intent_clarification import IntentClarificationRepository
from fitmind_agent.repositories.intent_clarification import _is_expired
from fitmind_agent.schemas.intent import IntentCandidate, IntentRecognitionResult
from fitmind_agent.services.intent_resolution_policy import IntentResolutionPolicy


INTENT_CATALOG = {
    "today_workout_record": ("记录训练", "保存今天完成或计划进行的训练内容"),
    "today_nutrition_record": ("记录饮食", "保存今天的饮食、补剂或营养摄入"),
    "today_body_status_record": ("记录身体状态", "保存睡眠、疲劳、体重或恢复情况"),
    "user_workout_plan_update": ("更新训练计划", "调整长期、阶段或周训练计划"),
    "recent_health_summary": ("查看近期状态", "汇总最近训练、饮食和恢复状态"),
    "today_workout_recommendation": ("推荐今天训练", "安排今天适合进行的训练"),
    "workout_history_query": ("查询训练历史", "查看已保存的训练记录"),
    "weekly_trend_report": ("查看周报趋势", "比较本周与上周的训练和恢复"),
    "general_chat": ("普通咨询", "进行健身知识问答或日常交流"),
}


class IntentClarificationService:
    def __init__(self, db: Session) -> None:
        self.repo = IntentClarificationRepository(db)
        self.policy = IntentResolutionPolicy()

    @staticmethod
    def is_cancel(message: str) -> bool:
        normalized = message.strip().lower()
        return any(word in normalized for word in ("取消", "算了", "不需要", "先不"))

    def create(self, *, user_id: int, session_id: int, query: str, result: IntentRecognitionResult):
        active = self.repo.get_active(user_id=user_id, session_id=session_id)
        if active:
            self.repo.update(active, {"status": "superseded", "resolved_at": datetime.now(timezone.utc)})
        candidates = self._candidates(result)
        question = self.build_question(candidates)
        return self.repo.create({
            "user_id": user_id,
            "session_id": session_id,
            "original_query": query,
            "candidate_intents": [item.model_dump() for item in candidates],
            "last_question": question,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        })

    def select(self, *, clarification_id: int, user_id: int, session_id: int, intent: str):
        record = self.repo.get_owned(clarification_id=clarification_id, user_id=user_id, session_id=session_id)
        if record is None or record.status != "pending":
            return None
        if _is_expired(record.expires_at):
            self.repo.update(record, {"status": "expired", "resolved_at": datetime.now(timezone.utc)})
            return None
        valid = {item.get("intent") for item in record.candidate_intents}
        if intent not in valid:
            return None
        return self.repo.update(record, {
            "status": "resolved", "resolved_intent": intent, "resolved_confidence": Decimal("1.000"),
            "resolution_source": "button", "resolved_at": datetime.now(timezone.utc),
        })

    def cancel(self, *, clarification_id: int, user_id: int, session_id: int):
        record = self.repo.get_owned(clarification_id=clarification_id, user_id=user_id, session_id=session_id)
        if record is None or record.status != "pending":
            return None
        if _is_expired(record.expires_at):
            self.repo.update(record, {"status": "expired", "resolved_at": datetime.now(timezone.utc)})
            return None
        return self.repo.update(record, {"status": "cancelled", "resolved_at": datetime.now(timezone.utc)})

    def retry(self, record, result: IntentRecognitionResult, answer: str):
        if not self.policy.needs_clarification(result):
            return self.repo.update(record, {
                "status": "resolved", "last_user_reply": answer, "resolved_intent": result.intent,
                "resolved_confidence": Decimal(str(result.confidence)), "resolution_source": "free_text",
                "resolved_at": datetime.now(timezone.utc),
            })
        if record.attempt_count >= record.max_attempts:
            return self.repo.update(record, {"status": "failed", "last_user_reply": answer, "resolved_at": datetime.now(timezone.utc)})
        candidates = self._candidates(result)
        return self.repo.update(record, {
            "attempt_count": record.attempt_count + 1, "last_user_reply": answer,
            "candidate_intents": [item.model_dump() for item in candidates],
            "last_question": self.build_question(candidates),
        })

    @staticmethod
    def _candidates(result: IntentRecognitionResult) -> list[IntentCandidate]:
        candidates = [item for item in result.candidates if item.intent in INTENT_CATALOG]
        if not candidates and result.intent in INTENT_CATALOG:
            candidates = [IntentCandidate(intent=result.intent, confidence=result.confidence, reason=result.reason)]
        if not candidates:
            candidates = [
                IntentCandidate(intent="today_workout_record", confidence=0.0),
                IntentCandidate(intent="today_nutrition_record", confidence=0.0),
            ]
        # A deterministic question must never expose unknown/internal labels.
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)[:3]

    @staticmethod
    def build_question(candidates: list[IntentCandidate]) -> str:
        labels = "，还是".join(INTENT_CATALOG[item.intent][0] for item in candidates)
        return f"我还不能确定你的主要需求。你是想{labels}？"

    @staticmethod
    def event(record, action: str = "requested") -> dict:
        options = [
            {"intent": item["intent"], "label": INTENT_CATALOG.get(item["intent"], (item["intent"], ""))[0],
             "description": INTENT_CATALOG.get(item["intent"], ("", ""))[1]}
            for item in record.candidate_intents
        ]
        return {"type": "clarification", "workflow": "intent_clarification", "action": action,
                "clarification_id": record.id, "question": record.last_question, "options": options,
                "attempt": record.attempt_count, "max_attempts": record.max_attempts, "status": record.status}
