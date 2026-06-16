from typing import Literal

from pydantic import BaseModel, Field


IntentCode = Literal[
    "today_workout_record",
    "recent_health_summary",
    "today_workout_recommendation",
    "today_nutrition_record",
    "today_body_status_record",
    "user_workout_plan_update",
    "general_chat",
    "unknown",
]


class KeywordIntentMatch(BaseModel):
    intent: IntentCode
    confidence: float = Field(ge=0.0, le=1.0)
    matched_keywords: list[str] = Field(default_factory=list)


class IntentRecognitionResult(BaseModel):
    intent: IntentCode
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["llm", "keyword", "fallback"]
    reason: str = ""
    keyword_match: KeywordIntentMatch | None = None


class IntentModuleRoute(BaseModel):
    intent: IntentCode
    module_name: str
    status: Literal["placeholder", "ready"] = "placeholder"
    db_intent_type: str
    description: str
