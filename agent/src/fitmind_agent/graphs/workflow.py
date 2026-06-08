from fitmind_agent.graphs.state import AgentState


def run_workflow(state: AgentState) -> AgentState:
    """
    Placeholder workflow.

    Later this will be replaced by a LangGraph StateGraph that routes
    plan/training/nutrition/body-status inputs into dedicated nodes.
    """
    message = state.get("message", "")
    lowered = message.lower()

    if "饮食" in message or "蛋白" in message or "eat" in lowered:
        intent = "nutrition"
        response_text = "已识别为饮食记录，后续将进入营养结构化流程。"
    elif "睡" in message or "疲劳" in message or "状态" in message:
        intent = "body_status"
        response_text = "已识别为身体状态记录，后续将进入状态结构化流程。"
    elif "计划" in message:
        intent = "plan"
        response_text = "已识别为训练计划，后续将进入计划解析流程。"
    elif "训练" in message or "完成" in message:
        intent = "training"
        response_text = "已识别为训练执行记录，后续将进入训练事实提取流程。"
    else:
        intent = "unknown"
        response_text = "已收到消息，后续将补充更完整的意图识别与追问流程。"

    return {
        **state,
        "intent": intent,
        "response_text": response_text,
    }
