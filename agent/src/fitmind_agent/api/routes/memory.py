from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from sqlalchemy.orm import Session

from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.memory import AgentDerivedMemoryCreate
from fitmind_agent.schemas.memory import AgentDerivedMemoryRead
from fitmind_agent.schemas.memory import AgentDerivedMemoryUpdate
from fitmind_agent.schemas.memory import ChatSessionCreate
from fitmind_agent.schemas.memory import ChatSessionRead
from fitmind_agent.schemas.memory import ChatSessionSummaryCreate
from fitmind_agent.schemas.memory import ChatSessionSummaryRead
from fitmind_agent.schemas.memory import ChatSessionSummaryUpdate
from fitmind_agent.schemas.memory import ChatSessionUpdate
from fitmind_agent.schemas.memory import UserDefinedMemoryCreate
from fitmind_agent.schemas.memory import UserDefinedMemoryRead
from fitmind_agent.schemas.memory import UserDefinedMemoryUpdate
from fitmind_agent.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memory"])


@router.post("/user-defined", response_model=UserDefinedMemoryRead)
def create_user_defined_memory(
    payload: UserDefinedMemoryCreate, db: Session = Depends(get_db_session)
) -> UserDefinedMemoryRead:
    return MemoryService(db).create_user_defined_memory(payload)


@router.get("/user-defined", response_model=list[UserDefinedMemoryRead])
def list_user_defined_memories(
    user_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[UserDefinedMemoryRead]:
    return MemoryService(db).list_user_defined_memories(user_id=user_id, status=status)


@router.patch("/user-defined/{memory_id}", response_model=UserDefinedMemoryRead)
def update_user_defined_memory(
    memory_id: int,
    payload: UserDefinedMemoryUpdate,
    db: Session = Depends(get_db_session),
) -> UserDefinedMemoryRead:
    record = MemoryService(db).update_user_defined_memory(memory_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="User defined memory not found")
    return record


@router.delete("/user-defined/{memory_id}")
def delete_user_defined_memory(memory_id: int, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    deleted = MemoryService(db).delete_user_defined_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User defined memory not found")
    return {"success": True}


@router.post("/agent-derived", response_model=AgentDerivedMemoryRead)
def create_agent_derived_memory(
    payload: AgentDerivedMemoryCreate, db: Session = Depends(get_db_session)
) -> AgentDerivedMemoryRead:
    return MemoryService(db).create_agent_derived_memory(payload)


@router.get("/agent-derived", response_model=list[AgentDerivedMemoryRead])
def list_agent_derived_memories(
    user_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[AgentDerivedMemoryRead]:
    return MemoryService(db).list_agent_derived_memories(user_id=user_id, status=status)


@router.patch("/agent-derived/{memory_id}", response_model=AgentDerivedMemoryRead)
def update_agent_derived_memory(
    memory_id: int,
    payload: AgentDerivedMemoryUpdate,
    db: Session = Depends(get_db_session),
) -> AgentDerivedMemoryRead:
    record = MemoryService(db).update_agent_derived_memory(memory_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="Agent derived memory not found")
    return record


@router.delete("/agent-derived/{memory_id}")
def delete_agent_derived_memory(memory_id: int, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    deleted = MemoryService(db).delete_agent_derived_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent derived memory not found")
    return {"success": True}


@router.post("/sessions", response_model=ChatSessionRead)
def create_chat_session(payload: ChatSessionCreate, db: Session = Depends(get_db_session)) -> ChatSessionRead:
    return MemoryService(db).create_chat_session(payload)


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_chat_sessions(
    user_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[ChatSessionRead]:
    return MemoryService(db).list_chat_sessions(user_id=user_id, status=status)


@router.patch("/sessions/{session_id}", response_model=ChatSessionRead)
def update_chat_session(
    session_id: int,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db_session),
) -> ChatSessionRead:
    record = MemoryService(db).update_chat_session(session_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return record


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: int, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    deleted = MemoryService(db).delete_chat_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True}


@router.post("/session-summaries", response_model=ChatSessionSummaryRead)
def create_chat_session_summary(
    payload: ChatSessionSummaryCreate, db: Session = Depends(get_db_session)
) -> ChatSessionSummaryRead:
    return MemoryService(db).create_chat_session_summary(payload)


@router.get("/session-summaries", response_model=list[ChatSessionSummaryRead])
def list_chat_session_summaries(
    session_id: int, db: Session = Depends(get_db_session)
) -> list[ChatSessionSummaryRead]:
    return MemoryService(db).list_chat_session_summaries(session_id=session_id)


@router.patch("/session-summaries/{summary_id}", response_model=ChatSessionSummaryRead)
def update_chat_session_summary(
    summary_id: int,
    payload: ChatSessionSummaryUpdate,
    db: Session = Depends(get_db_session),
) -> ChatSessionSummaryRead:
    record = MemoryService(db).update_chat_session_summary(summary_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session summary not found")
    return record


@router.delete("/session-summaries/{summary_id}")
def delete_chat_session_summary(summary_id: int, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    deleted = MemoryService(db).delete_chat_session_summary(summary_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session summary not found")
    return {"success": True}
