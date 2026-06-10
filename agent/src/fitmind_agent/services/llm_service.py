from collections.abc import Iterator

from fitmind_agent.core.llm import DeepSeekLLMClient
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMChatResponse


class LLMService:
    """
    High-level LLM service wrapper used by Agent workflows and business services.
    """

    def __init__(self, client: DeepSeekLLMClient | None = None) -> None:
        self.client = client or DeepSeekLLMClient()

    def generate(self, request: LLMChatRequest) -> LLMChatResponse:
        return self.client.chat(request)

    def stream(self, request: LLMChatRequest) -> Iterator[tuple[str, str | None]]:
        return self.client.stream_chat(request)

    def generate_text(
        self,
        user_text: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        return self.client.chat_text(
            user_text=user_text,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
        )
