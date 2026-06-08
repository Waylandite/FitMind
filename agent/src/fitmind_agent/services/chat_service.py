from fitmind_agent.graphs.workflow import run_workflow
from fitmind_agent.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    def handle(self, payload: ChatRequest) -> ChatResponse:
        result = run_workflow(
            {
                "user_id": payload.user_id,
                "thread_id": payload.thread_id,
                "message": payload.message,
            }
        )

        return ChatResponse(
            user_id=payload.user_id,
            thread_id=payload.thread_id,
            intent=result.get("intent", "unknown"),
            reply=result.get("response_text", ""),
        )
