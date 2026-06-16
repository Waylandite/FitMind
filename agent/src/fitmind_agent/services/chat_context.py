from __future__ import annotations

from fitmind_agent.repositories.memory import ChatSessionSummaryRepository
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.schemas.chat import ChatRequest
from fitmind_agent.schemas.llm import LLMMessage
from fitmind_agent.services.prompt_loader import PromptLoader


class ConversationContextBuilder:
    """
    Builder pattern for assembling LLM prompt context from persisted chat history.

    Current strategy:
    - read the latest messages from the current session
    - keep at most the previous 5 rounds (10 messages)
    - append the current user input at the end
    """

    def __init__(
        self,
        conversation_log_repository: ConversationLogRepository,
        summary_repository: ChatSessionSummaryRepository | None = None,
        recent_context_rounds: int = 5,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.conversation_log_repository = conversation_log_repository
        self.summary_repository = summary_repository
        self.recent_context_rounds = recent_context_rounds
        self.prompt_loader = prompt_loader or PromptLoader()

    def build_messages(self, payload: ChatRequest, session_id: int | None = None) -> list[LLMMessage]:
        messages: list[LLMMessage] = []

        messages.append(
            LLMMessage(
                role="system",
                content=payload.system_prompt or self.prompt_loader.load("global/system.txt"),
            )
        )

        summary_message = self._build_summary_message(session_id=session_id)
        if summary_message is not None:
            messages.append(summary_message)

        messages.extend(self._build_recent_context_messages(session_id=session_id))
        messages.append(LLMMessage(role="user", content=payload.message))
        return messages

    def _build_summary_message(self, session_id: int | None = None) -> LLMMessage | None:
        if session_id is None or self.summary_repository is None:
            return None

        latest_summary = self.summary_repository.get_latest_by_session_and_type(
            session_id=session_id,
            summary_type="running_summary",
        )
        if latest_summary is None or not latest_summary.summary_text.strip():
            return None

        return LLMMessage(
            role="system",
            content=f"以下是当前 session 较早历史的压缩摘要，请结合它理解后续对话：\n{latest_summary.summary_text}",
        )

    def _build_recent_context_messages(self, session_id: int | None = None) -> list[LLMMessage]:
        if session_id is None:
            return []

        recent_logs = self.conversation_log_repository.list_recent_by_session(
            session_id=session_id,
            limit=self.recent_context_rounds * 2,
        )

        return [
            LLMMessage(role=log.role, content=log.message_text)
            for log in recent_logs
            if log.role in {"user", "assistant", "system"}
        ]
