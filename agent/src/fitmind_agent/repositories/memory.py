from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import AgentDerivedMemory
from fitmind_agent.db.models import ChatSession
from fitmind_agent.db.models import ChatSessionSummary
from fitmind_agent.db.models import ConversationLog
from fitmind_agent.db.models import UserDefinedMemory


class UserDefinedMemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> UserDefinedMemory:
        memory = UserDefinedMemory(**dict(data))
        self.session.add(memory)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def get_by_id(self, memory_id: int) -> UserDefinedMemory | None:
        return self.session.get(UserDefinedMemory, memory_id)

    def list_by_user(self, user_id: int, status: str | None = None) -> list[UserDefinedMemory]:
        stmt = select(UserDefinedMemory).where(UserDefinedMemory.user_id == user_id)
        if status:
            stmt = stmt.where(UserDefinedMemory.status == status)
        stmt = stmt.order_by(UserDefinedMemory.priority.desc(), UserDefinedMemory.id.desc())
        return list(self.session.scalars(stmt))

    def update(self, memory: UserDefinedMemory, data: Mapping[str, Any]) -> UserDefinedMemory:
        for key, value in data.items():
            setattr(memory, key, value)
        self.session.add(memory)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def delete(self, memory: UserDefinedMemory) -> None:
        self.session.delete(memory)
        self.session.commit()


class AgentDerivedMemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> AgentDerivedMemory:
        memory = AgentDerivedMemory(**dict(data))
        self.session.add(memory)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def get_by_id(self, memory_id: int) -> AgentDerivedMemory | None:
        return self.session.get(AgentDerivedMemory, memory_id)

    def list_by_user(self, user_id: int, status: str | None = None) -> list[AgentDerivedMemory]:
        stmt = select(AgentDerivedMemory).where(AgentDerivedMemory.user_id == user_id)
        if status:
            stmt = stmt.where(AgentDerivedMemory.status == status)
        stmt = stmt.order_by(AgentDerivedMemory.id.desc())
        return list(self.session.scalars(stmt))

    def update(self, memory: AgentDerivedMemory, data: Mapping[str, Any]) -> AgentDerivedMemory:
        for key, value in data.items():
            setattr(memory, key, value)
        self.session.add(memory)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def delete(self, memory: AgentDerivedMemory) -> None:
        self.session.delete(memory)
        self.session.commit()


class ChatSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> ChatSession:
        chat_session = ChatSession(**dict(data))
        self.session.add(chat_session)
        self.session.commit()
        self.session.refresh(chat_session)
        return chat_session

    def get_by_id(self, session_id: int) -> ChatSession | None:
        return self.session.get(ChatSession, session_id)

    def list_by_user(self, user_id: int, status: str | None = None) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        if status:
            stmt = stmt.where(ChatSession.status == status)
        stmt = stmt.order_by(ChatSession.last_message_at.desc(), ChatSession.id.desc())
        return list(self.session.scalars(stmt))

    def get_latest_by_thread(self, user_id: int, thread_id: str) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.thread_id == thread_id)
            .order_by(ChatSession.session_no.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def create_next_for_thread(self, user_id: int, thread_id: str, title: str | None = None) -> ChatSession:
        latest = self.get_latest_by_thread(user_id=user_id, thread_id=thread_id)
        next_no = 1 if latest is None else latest.session_no + 1
        return self.create(
            {
                "user_id": user_id,
                "thread_id": thread_id,
                "session_no": next_no,
                "title": title,
                "status": "active",
                "last_message_at": datetime.now(),
            }
        )

    def update(self, chat_session: ChatSession, data: Mapping[str, Any]) -> ChatSession:
        for key, value in data.items():
            setattr(chat_session, key, value)
        self.session.add(chat_session)
        self.session.commit()
        self.session.refresh(chat_session)
        return chat_session

    def delete(self, chat_session: ChatSession) -> None:
        self.session.delete(chat_session)
        self.session.commit()


class ChatSessionSummaryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> ChatSessionSummary:
        summary = ChatSessionSummary(**dict(data))
        self.session.add(summary)
        self.session.commit()
        self.session.refresh(summary)
        return summary

    def get_by_id(self, summary_id: int) -> ChatSessionSummary | None:
        return self.session.get(ChatSessionSummary, summary_id)

    def list_by_session(self, session_id: int) -> list[ChatSessionSummary]:
        stmt = (
            select(ChatSessionSummary)
            .where(ChatSessionSummary.session_id == session_id)
            .order_by(ChatSessionSummary.summary_version.desc(), ChatSessionSummary.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_latest_by_session_and_type(
        self, session_id: int, summary_type: str = "running_summary"
    ) -> ChatSessionSummary | None:
        stmt = (
            select(ChatSessionSummary)
            .where(
                ChatSessionSummary.session_id == session_id,
                ChatSessionSummary.summary_type == summary_type,
            )
            .order_by(ChatSessionSummary.summary_version.desc(), ChatSessionSummary.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def update(self, summary: ChatSessionSummary, data: Mapping[str, Any]) -> ChatSessionSummary:
        for key, value in data.items():
            setattr(summary, key, value)
        self.session.add(summary)
        self.session.commit()
        self.session.refresh(summary)
        return summary

    def delete(self, summary: ChatSessionSummary) -> None:
        self.session.delete(summary)
        self.session.commit()


class ConversationLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent_by_session(self, session_id: int, limit: int = 10) -> list[ConversationLog]:
        stmt = (
            select(ConversationLog)
            .where(ConversationLog.session_id == session_id)
            .order_by(ConversationLog.id.desc())
            .limit(limit)
        )
        rows = list(self.session.scalars(stmt))
        rows.reverse()
        return rows

    def list_between_session_watermarks(
        self,
        session_id: int,
        *,
        after_log_id: int | None = None,
        before_log_id: int | None = None,
    ) -> list[ConversationLog]:
        stmt = select(ConversationLog).where(ConversationLog.session_id == session_id)
        if after_log_id is not None:
            stmt = stmt.where(ConversationLog.id > after_log_id)
        if before_log_id is not None:
            stmt = stmt.where(ConversationLog.id < before_log_id)
        stmt = stmt.order_by(ConversationLog.id.asc())
        return list(self.session.scalars(stmt))

    def create(
        self,
        *,
        user_id: int,
        thread_id: str,
        role: str,
        message_text: str,
        session_id: int | None = None,
        record_date: date | None = None,
        intent_type: str | None = None,
    ) -> ConversationLog:
        log = ConversationLog(
            user_id=user_id,
            thread_id=thread_id,
            session_id=session_id,
            record_date=record_date,
            role=role,
            message_text=message_text,
            intent_type=intent_type,
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
