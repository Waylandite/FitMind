from __future__ import annotations

from fitmind_agent.schemas.intent import IntentCode
from fitmind_agent.schemas.intent import IntentModuleRoute
from fitmind_agent.schemas.intent import IntentRecognitionResult


INTENT_ROUTES: dict[IntentCode, IntentModuleRoute] = {
    "today_workout_record": IntentModuleRoute(
        intent="today_workout_record",
        module_name="workout_record_writer",
        db_intent_type="workout",
        description="已接入当日训练记录提取、确认和落库模块。",
        status="ready",
    ),
    "recent_workout_summary": IntentModuleRoute(
        intent="recent_workout_summary",
        module_name="workout_summary_agent",
        db_intent_type="query",
        description="待接入最近训练情况总结模块。",
    ),
    "today_workout_recommendation": IntentModuleRoute(
        intent="today_workout_recommendation",
        module_name="workout_recommendation_agent",
        db_intent_type="plan",
        description="待接入当日训练计划推荐模块。",
    ),
    "today_nutrition_record": IntentModuleRoute(
        intent="today_nutrition_record",
        module_name="nutrition_record_react_writer",
        db_intent_type="nutrition",
        description="已接入饮食记录解析、ReAct 工具接入预留和落库模块。",
        status="ready",
    ),
    "today_body_status_record": IntentModuleRoute(
        intent="today_body_status_record",
        module_name="body_status_writer",
        db_intent_type="body_status",
        description="已接入睡眠和身体状态解析及落库模块。",
        status="ready",
    ),
    "user_workout_plan_update": IntentModuleRoute(
        intent="user_workout_plan_update",
        module_name="workout_plan_updater",
        db_intent_type="plan",
        description="待接入用户长期健身计划更新模块。",
    ),
    "general_chat": IntentModuleRoute(
        intent="general_chat",
        module_name="general_chat",
        db_intent_type="query",
        description="普通对话模块。",
        status="ready",
    ),
    "unknown": IntentModuleRoute(
        intent="unknown",
        module_name="clarification_agent",
        db_intent_type="query",
        description="待接入澄清追问模块。",
    ),
}


class IntentRouter:
    def route(self, intent_result: IntentRecognitionResult) -> IntentModuleRoute:
        return INTENT_ROUTES.get(intent_result.intent, INTENT_ROUTES["unknown"])
