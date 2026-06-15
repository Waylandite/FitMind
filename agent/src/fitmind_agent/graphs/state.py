"""Deprecated placeholder — not used in current architecture.

The intent types defined here ("plan", "training", "nutrition", "body_status",
"unknown") are superseded by the IntentCode Literal in:

  schemas/intent.py

Actual intent codes:
  today_workout_record, recent_workout_summary, today_workout_recommendation,
  today_nutrition_record, today_body_status_record, user_workout_plan_update,
  general_chat, unknown
"""

from typing import Literal, TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    thread_id: str
    message: str
    intent: Literal["plan", "training", "nutrition", "body_status", "unknown"]
    response_text: str
