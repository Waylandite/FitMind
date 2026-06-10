from __future__ import annotations

from collections.abc import Iterator
from functools import cached_property

from openai import OpenAI

from fitmind_agent.core.config import get_settings
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMChatResponse
from fitmind_agent.schemas.llm import LLMMessage


class LLMConfigurationError(RuntimeError):
    """Raised when LLM configuration is incomplete."""


class DeepSeekLLMClient:
    """
    OpenAI-compatible client wrapper for https://api.deepseek.com.

    This class centralizes:
    - API key / base URL management
    - default model and temperature
    - chat completion request formatting
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        default_temperature: float | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.default_model = default_model or settings.llm_model
        self.default_temperature = (
            default_temperature
            if default_temperature is not None
            else settings.llm_temperature
        )

        if not self.api_key:
            raise LLMConfigurationError(
                "FITMIND_LLM_API_KEY is missing. Please configure the DeepSeek API key in the environment."
            )

    @cached_property
    def client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        response = self.client.chat.completions.create(
            model=request.model or self.default_model,
            messages=[message.model_dump() for message in request.messages],
            temperature=(
                request.temperature
                if request.temperature is not None
                else self.default_temperature
            ),
        )

        content = response.choices[0].message.content or ""

        return LLMChatResponse(
            model=response.model,
            content=content,
            raw_response=response.model_dump(),
        )

    def stream_chat(self, request: LLMChatRequest) -> Iterator[tuple[str, str | None]]:
        stream = self.client.chat.completions.create(
            model=request.model or self.default_model,
            messages=[message.model_dump() for message in request.messages],
            temperature=(
                request.temperature
                if request.temperature is not None
                else self.default_temperature
            ),
            stream=True,
        )

        model_name = request.model or self.default_model
        for chunk in stream:
            model_name = getattr(chunk, "model", None) or model_name
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content, model_name

    def chat_text(
        self,
        user_text: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        messages: list[LLMMessage] = []

        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        messages.append(LLMMessage(role="user", content=user_text))

        result = self.chat(
            LLMChatRequest(
                messages=messages,
                model=model,
                temperature=temperature,
            )
        )
        return result.content


YunwuLLMClient = DeepSeekLLMClient
