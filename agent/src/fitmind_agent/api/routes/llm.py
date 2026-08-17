from fastapi import APIRouter
from fastapi import HTTPException
from uuid import uuid4

from fitmind_agent.api.dependencies import CurrentUser
from fitmind_agent.core.llm import LLMConfigurationError
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMChatResponse
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.token_usage_tracker import TokenUsageContext
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker

router = APIRouter(tags=["llm"])


@router.post("/llm/chat", response_model=LLMChatResponse)
def llm_chat(payload: LLMChatRequest, current_user: CurrentUser) -> LLMChatResponse:
    try:
        with TokenUsageTracker.context(
            TokenUsageContext(
                request_id=uuid4().hex,
                user_id=current_user.id,
                workflow="direct_llm",
                node_name="llm_chat",
            )
        ):
            return LLMService().generate(payload)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=f"LLM request failed: {exc}") from exc
