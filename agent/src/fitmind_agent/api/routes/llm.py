from fastapi import APIRouter
from fastapi import HTTPException

from fitmind_agent.core.llm import LLMConfigurationError
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMChatResponse
from fitmind_agent.services.llm_service import LLMService

router = APIRouter(tags=["llm"])


@router.post("/llm/chat", response_model=LLMChatResponse)
def llm_chat(payload: LLMChatRequest) -> LLMChatResponse:
    try:
        service = LLMService()
        return service.generate(payload)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=f"LLM request failed: {exc}") from exc
