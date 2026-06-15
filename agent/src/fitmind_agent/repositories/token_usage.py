from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import ChatTurnTokenUsage
from fitmind_agent.db.models import LLMCallLog


class TokenUsageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_call_log(self, data: Mapping[str, Any]) -> LLMCallLog:
        log = LLMCallLog(**dict(data))
        self.session.add(log)
        self.session.commit()
        return log

    def upsert_turn_usage(self, data: Mapping[str, Any]) -> None:
        values = dict(data)
        existing = self.session.scalar(
            select(ChatTurnTokenUsage).where(
                ChatTurnTokenUsage.request_id == values["request_id"]
            )
        )
        if existing is None:
            self.session.add(ChatTurnTokenUsage(**values))
        else:
            for key, value in values.items():
                if key != "request_id":
                    setattr(existing, key, value)
            self.session.add(existing)
        self.session.commit()

    def aggregate_calls_by_request(self, request_id: str) -> dict[str, Any]:
        stmt = select(LLMCallLog).where(LLMCallLog.request_id == request_id)
        calls = list(self.session.scalars(stmt))
        model_breakdown: dict[str, dict[str, int]] = {}
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        for call in calls:
            model_key = call.model
            bucket = model_breakdown.setdefault(
                model_key,
                {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "call_count": 0,
                },
            )
            prompt_tokens = call.prompt_tokens or 0
            completion_tokens = call.completion_tokens or 0
            call_total_tokens = call.total_tokens or prompt_tokens + completion_tokens
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += call_total_tokens
            bucket["prompt_tokens"] += prompt_tokens
            bucket["completion_tokens"] += completion_tokens
            bucket["total_tokens"] += call_total_tokens
            bucket["call_count"] += 1

        return {
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "llm_call_count": len(calls),
            "model_breakdown": model_breakdown,
        }
