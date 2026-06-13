from __future__ import annotations

from sqlalchemy.orm import Session

from fitmind_agent.repositories.memory import AgentDerivedMemoryRepository
from fitmind_agent.repositories.memory import ChatSessionRepository
from fitmind_agent.repositories.memory import ChatSessionSummaryRepository
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.repositories.memory import UserDefinedMemoryRepository
from fitmind_agent.schemas.memory import AgentDerivedMemoryCreate
from fitmind_agent.schemas.memory import AgentDerivedMemoryRead
from fitmind_agent.schemas.memory import AgentDerivedMemoryUpdate
from fitmind_agent.schemas.memory import ChatSessionCreate
from fitmind_agent.schemas.memory import ChatSessionRead
from fitmind_agent.schemas.memory import ChatSessionSummaryCreate
from fitmind_agent.schemas.memory import ChatSessionSummaryRead
from fitmind_agent.schemas.memory import ChatSessionSummaryUpdate
from fitmind_agent.schemas.memory import ChatSessionUpdate
from fitmind_agent.schemas.memory import ConversationLogRead
from fitmind_agent.schemas.memory import UserDefinedMemoryCreate
from fitmind_agent.schemas.memory import UserDefinedMemoryRead
from fitmind_agent.schemas.memory import UserDefinedMemoryUpdate


class MemoryService:
    def __init__(self, db: Session) -> None:
        self.user_defined_repo = UserDefinedMemoryRepository(db)
        self.agent_derived_repo = AgentDerivedMemoryRepository(db)
        self.chat_session_repo = ChatSessionRepository(db)
        self.summary_repo = ChatSessionSummaryRepository(db)
        self.conversation_log_repo = ConversationLogRepository(db)

    def create_user_defined_memory(self, payload: UserDefinedMemoryCreate) -> UserDefinedMemoryRead:
        memory = self.user_defined_repo.create(payload.model_dump())
        return UserDefinedMemoryRead.model_validate(memory)

    def list_user_defined_memories(self, user_id: int, status: str | None = None) -> list[UserDefinedMemoryRead]:
        records = self.user_defined_repo.list_by_user(user_id=user_id, status=status)
        return [UserDefinedMemoryRead.model_validate(record) for record in records]

    def update_user_defined_memory(
        self, memory_id: int, payload: UserDefinedMemoryUpdate
    ) -> UserDefinedMemoryRead | None:
        memory = self.user_defined_repo.get_by_id(memory_id)
        if memory is None:
            return None
        updated = self.user_defined_repo.update(memory, payload.model_dump(exclude_unset=True))
        return UserDefinedMemoryRead.model_validate(updated)

    def delete_user_defined_memory(self, memory_id: int) -> bool:
        memory = self.user_defined_repo.get_by_id(memory_id)
        if memory is None:
            return False
        self.user_defined_repo.delete(memory)
        return True

    def create_agent_derived_memory(self, payload: AgentDerivedMemoryCreate) -> AgentDerivedMemoryRead:
        memory = self.agent_derived_repo.create(payload.model_dump())
        return AgentDerivedMemoryRead.model_validate(memory)

    def list_agent_derived_memories(self, user_id: int, status: str | None = None) -> list[AgentDerivedMemoryRead]:
        records = self.agent_derived_repo.list_by_user(user_id=user_id, status=status)
        return [AgentDerivedMemoryRead.model_validate(record) for record in records]

    def update_agent_derived_memory(
        self, memory_id: int, payload: AgentDerivedMemoryUpdate
    ) -> AgentDerivedMemoryRead | None:
        memory = self.agent_derived_repo.get_by_id(memory_id)
        if memory is None:
            return None
        updated = self.agent_derived_repo.update(memory, payload.model_dump(exclude_unset=True))
        return AgentDerivedMemoryRead.model_validate(updated)

    def delete_agent_derived_memory(self, memory_id: int) -> bool:
        memory = self.agent_derived_repo.get_by_id(memory_id)
        if memory is None:
            return False
        self.agent_derived_repo.delete(memory)
        return True

    def create_chat_session(self, payload: ChatSessionCreate) -> ChatSessionRead:
        data = payload.model_dump(exclude_none=True)
        chat_session = self.chat_session_repo.create(data)
        return ChatSessionRead.model_validate(chat_session)

    def list_chat_sessions(self, user_id: int, status: str | None = None) -> list[ChatSessionRead]:
        records = self.chat_session_repo.list_by_user(user_id=user_id, status=status)
        return [ChatSessionRead.model_validate(record) for record in records]

    def update_chat_session(self, session_id: int, payload: ChatSessionUpdate) -> ChatSessionRead | None:
        chat_session = self.chat_session_repo.get_by_id(session_id)
        if chat_session is None:
            return None
        updated = self.chat_session_repo.update(chat_session, payload.model_dump(exclude_unset=True))
        return ChatSessionRead.model_validate(updated)

    def delete_chat_session(self, session_id: int) -> bool:
        chat_session = self.chat_session_repo.get_by_id(session_id)
        if chat_session is None:
            return False
        self.chat_session_repo.delete(chat_session)
        return True

    def create_chat_session_summary(self, payload: ChatSessionSummaryCreate) -> ChatSessionSummaryRead:
        summary = self.summary_repo.create(payload.model_dump())
        return ChatSessionSummaryRead.model_validate(summary)

    def list_chat_session_summaries(self, session_id: int) -> list[ChatSessionSummaryRead]:
        records = self.summary_repo.list_by_session(session_id=session_id)
        return [ChatSessionSummaryRead.model_validate(record) for record in records]

    def update_chat_session_summary(
        self, summary_id: int, payload: ChatSessionSummaryUpdate
    ) -> ChatSessionSummaryRead | None:
        summary = self.summary_repo.get_by_id(summary_id)
        if summary is None:
            return None
        updated = self.summary_repo.update(summary, payload.model_dump(exclude_unset=True))
        return ChatSessionSummaryRead.model_validate(updated)

    def delete_chat_session_summary(self, summary_id: int) -> bool:
        summary = self.summary_repo.get_by_id(summary_id)
        if summary is None:
            return False
        self.summary_repo.delete(summary)
        return True

    def list_session_messages(self, session_id: int) -> list[ConversationLogRead]:
        records = self.conversation_log_repo.list_all_by_session(session_id=session_id)
        return [ConversationLogRead.model_validate(record) for record in records]
