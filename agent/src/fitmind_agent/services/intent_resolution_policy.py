from __future__ import annotations

from fitmind_agent.schemas.intent import IntentRecognitionResult


WRITE_INTENTS = {
    "today_workout_record", "today_nutrition_record", "today_body_status_record",
    "user_workout_plan_update",
}
QUERY_INTENTS = {
    "recent_health_summary", "today_workout_recommendation", "workout_history_query",
    "weekly_trend_report",
}


class IntentResolutionPolicy:
    """Deterministic safety gate: model output alone never authorizes a write."""

    @staticmethod
    def threshold(intent: str) -> float:
        if intent in WRITE_INTENTS:
            return 0.78
        if intent in QUERY_INTENTS:
            return 0.70
        if intent == "general_chat":
            return 0.65
        return 1.01

    def needs_clarification(self, result: IntentRecognitionResult) -> bool:
        candidates = result.candidates or []
        if result.intent == "unknown" or result.confidence < self.threshold(result.intent):
            return True
        # Candidate order is model supplied, therefore normalize it before using
        # it as a safety decision.
        ranked = sorted(candidates, key=lambda item: item.confidence, reverse=True)
        if ranked and ranked[0].intent != result.intent:
            return True
        if len(ranked) > 1 and ranked[0].confidence - ranked[1].confidence < 0.15:
            return True
        return len({item.intent for item in ranked[:3]} & WRITE_INTENTS) > 1
