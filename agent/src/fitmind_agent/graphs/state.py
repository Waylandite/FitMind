from typing import Literal, TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    thread_id: str
    message: str
    intent: Literal["plan", "training", "nutrition", "body_status", "unknown"]
    response_text: str
