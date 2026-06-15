from __future__ import annotations

from collections.abc import Iterator
from functools import cached_property
import time
from typing import Any

from openai import OpenAI

from fitmind_agent.core.config import get_settings
from fitmind_agent.schemas.llm import LLMChatRequest
from fitmind_agent.schemas.llm import LLMChatResponse
from fitmind_agent.schemas.llm import LLMMessage
from fitmind_agent.services.token_usage_tracker import TokenUsageTracker


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
        started_at = time.perf_counter()
        model = request.model or self.default_model
        messages = [message.model_dump() for message in request.messages]
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=(
                    request.temperature
                    if request.temperature is not None
                    else self.default_temperature
                ),
            )
        except Exception as exc:
            TokenUsageTracker.record_call(
                provider="deepseek",
                model=model,
                is_stream=False,
                started_at=started_at,
                usage=self._estimate_usage(messages=messages, output_text=""),
                success=False,
                error_message=str(exc),
            )
            raise

        content = response.choices[0].message.content or ""
        usage = self._extract_usage(response.model_dump()) or self._estimate_usage(
            messages=messages,
            output_text=content,
        )
        TokenUsageTracker.record_call(
            provider="deepseek",
            model=response.model or model,
            is_stream=False,
            started_at=started_at,
            usage=usage,
            success=True,
        )

        return LLMChatResponse(
            model=response.model,
            content=content,
            raw_response=response.model_dump(),
            usage=usage,
        )

    def stream_chat(self, request: LLMChatRequest) -> Iterator[tuple[str, str | None]]:
        started_at = time.perf_counter()
        model = request.model or self.default_model
        messages = [message.model_dump() for message in request.messages]
        output_parts: list[str] = []
        usage: dict[str, Any] | None = None
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=(
                request.temperature
                if request.temperature is not None
                else self.default_temperature
            ),
            stream=True,
        )

        model_name = model
        try:
            for chunk in stream:
                chunk_dump = chunk.model_dump() if hasattr(chunk, "model_dump") else {}
                usage = self._extract_usage(chunk_dump) or usage
                model_name = getattr(chunk, "model", None) or model_name
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    output_parts.append(content)
                    yield content, model_name
        except Exception as exc:
            TokenUsageTracker.record_call(
                provider="deepseek",
                model=model_name,
                is_stream=True,
                started_at=started_at,
                usage=usage or self._estimate_usage(messages=messages, output_text="".join(output_parts)),
                success=False,
                error_message=str(exc),
            )
            raise
        else:
            TokenUsageTracker.record_call(
                provider="deepseek",
                model=model_name,
                is_stream=True,
                started_at=started_at,
                usage=usage or self._estimate_usage(messages=messages, output_text="".join(output_parts)),
                success=True,
            )

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

    @staticmethod
    def _extract_usage(raw_response: dict[str, Any]) -> dict[str, Any] | None:
        usage = raw_response.get("usage")
        if isinstance(usage, dict) and usage:
            return usage
        return None

    @classmethod
    def _estimate_usage(cls, *, messages: list[dict[str, Any]], output_text: str) -> dict[str, Any]:
        prompt_text = "\n".join(str(message.get("content") or "") for message in messages)
        prompt_tokens = cls._estimate_token_count(prompt_text)
        completion_tokens = cls._estimate_token_count(output_text)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated": True,
        }

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        if not text:
            return 0
        cjk_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        non_cjk_chars = max(len(text) - cjk_chars, 0)
        return max(cjk_chars + (non_cjk_chars + 3) // 4, 1)


YunwuLLMClient = DeepSeekLLMClient
