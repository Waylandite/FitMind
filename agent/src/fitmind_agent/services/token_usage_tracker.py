from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fitmind_agent.db.session import SessionLocal
from fitmind_agent.repositories.token_usage import TokenUsageRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenUsageContext:
    request_id: str
    user_id: int | None = None
    thread_id: str | None = None
    session_id: int | None = None
    workflow: str | None = None
    node_name: str | None = None


_current_context: ContextVar[TokenUsageContext | None] = ContextVar(
    "fitmind_token_usage_context",
    default=None,
)


class TokenUsageTracker:
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="token-usage")
    _futures: list[Future] = []
    _futures_lock = Lock()

    @staticmethod
    @contextmanager
    def context(context: TokenUsageContext) -> Iterator[None]:
        token = _current_context.set(context)
        try:
            yield
        finally:
            _current_context.reset(token)

    @staticmethod
    @contextmanager
    def scoped(*, workflow: str | None = None, node_name: str | None = None) -> Iterator[None]:
        current = _current_context.get()
        if current is None:
            yield
            return

        next_context = TokenUsageContext(
            request_id=current.request_id,
            user_id=current.user_id,
            thread_id=current.thread_id,
            session_id=current.session_id,
            workflow=workflow or current.workflow,
            node_name=node_name or current.node_name,
        )
        token = _current_context.set(next_context)
        try:
            yield
        finally:
            _current_context.reset(token)

    @staticmethod
    def current_context() -> TokenUsageContext | None:
        return _current_context.get()

    @classmethod
    def record_call(
        cls,
        *,
        provider: str,
        model: str,
        is_stream: bool,
        started_at: float,
        usage: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        context = cls.current_context()
        if context is None:
            return

        usage_data = usage or {}
        prompt_tokens = cls._int_or_none(
            usage_data.get("prompt_tokens")
            or usage_data.get("input_tokens")
        )
        completion_tokens = cls._int_or_none(
            usage_data.get("completion_tokens")
            or usage_data.get("output_tokens")
        )
        total_tokens = cls._int_or_none(
            usage_data.get("total_tokens")
            or (
                prompt_tokens + completion_tokens
                if prompt_tokens is not None and completion_tokens is not None
                else None
            )
        )
        completion_details = usage_data.get("completion_tokens_details") or {}
        prompt_details = usage_data.get("prompt_tokens_details") or {}

        data = {
            "request_id": context.request_id,
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "session_id": context.session_id,
            "workflow": context.workflow,
            "node_name": context.node_name,
            "provider": provider,
            "model": model,
            "is_stream": is_stream,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": cls._int_or_none(completion_details.get("reasoning_tokens")),
            "cached_tokens": cls._int_or_none(prompt_details.get("cached_tokens")),
            "usage_source": cls._usage_source(usage_data),
            "latency_ms": max(int((time.perf_counter() - started_at) * 1000), 0),
            "success": success,
            "error_message": error_message,
            "raw_usage": usage_data or None,
        }
        cls._track_future(cls._executor.submit(cls._safe_create_call_log, data))

    @classmethod
    def aggregate_turn(
        cls,
        *,
        request_id: str,
        user_id: int | None,
        thread_id: str | None,
        session_id: int | None,
        intent_type: str | None,
    ) -> None:
        pending_futures = cls._snapshot_futures()
        cls._track_future(cls._executor.submit(
            cls._safe_aggregate_turn_after,
            pending_futures,
            {
                "request_id": request_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": session_id,
                "intent_type": intent_type,
            },
        ))

    @staticmethod
    def flush_for_tests() -> None:
        for future in TokenUsageTracker._snapshot_futures():
            future.result(timeout=10)

    @staticmethod
    def _safe_create_call_log(data: dict[str, Any]) -> None:
        try:
            with SessionLocal() as session:
                TokenUsageRepository(session).create_call_log(data)
        except Exception:
            logger.exception("Failed to persist LLM token usage call log.")

    @staticmethod
    def _safe_aggregate_turn(context: dict[str, Any]) -> None:
        try:
            with SessionLocal() as session:
                repo = TokenUsageRepository(session)
                aggregate = repo.aggregate_calls_by_request(context["request_id"])
                repo.upsert_turn_usage({**context, **aggregate})
        except Exception:
            logger.exception("Failed to aggregate chat turn token usage.")

    @staticmethod
    def _safe_aggregate_turn_after(pending_futures: list[Future], context: dict[str, Any]) -> None:
        for future in pending_futures:
            try:
                future.result(timeout=10)
            except Exception:
                logger.exception("Token usage call log future failed before aggregation.")
        TokenUsageTracker._safe_aggregate_turn(context)

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _usage_source(usage_data: dict[str, Any]) -> str:
        if not usage_data:
            return "unavailable"
        if usage_data.get("estimated"):
            return "estimated"
        return "provider"

    @classmethod
    def _track_future(cls, future: Future) -> None:
        with cls._futures_lock:
            cls._futures = [item for item in cls._futures if not item.done()]
            cls._futures.append(future)

    @classmethod
    def _snapshot_futures(cls) -> list[Future]:
        with cls._futures_lock:
            cls._futures = [item for item in cls._futures if not item.done()]
            return list(cls._futures)
