from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from fitmind_agent.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="chk_users_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[UserProfile | None] = relationship(back_populates="user", uselist=False)
    workout_plans: Mapped[list[UserWorkoutPlan]] = relationship(back_populates="user")
    workout_records: Mapped[list[UserWorkoutRecord]] = relationship(back_populates="user")
    nutrition_records: Mapped[list[UserNutritionRecord]] = relationship(back_populates="user")
    body_status_records: Mapped[list[UserBodyStatusRecord]] = relationship(back_populates="user")
    conversation_logs: Mapped[list[ConversationLog]] = relationship(back_populates="user")
    intent_recognition_logs: Mapped[list[IntentRecognitionLog]] = relationship(back_populates="user")
    defined_memories: Mapped[list[UserDefinedMemory]] = relationship(back_populates="user")
    derived_memories: Mapped[list[AgentDerivedMemory]] = relationship(back_populates="user")
    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="user")
    workout_record_drafts: Mapped[list[WorkoutRecordDraft]] = relationship(back_populates="user")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profiles_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    goal_type: Mapped[str | None] = mapped_column(String(50))
    training_level: Mapped[str | None] = mapped_column(String(50))
    injury_notes: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    diet_preference: Mapped[str | None] = mapped_column(Text)
    preferred_training_days: Mapped[str | None] = mapped_column(Text)
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="profile")


class UserWorkoutPlan(Base, TimestampMixin):
    __tablename__ = "user_workout_plans"
    __table_args__ = (
        CheckConstraint("source IN ('manual', 'agent')", name="chk_user_workout_plans_source"),
        CheckConstraint("status IN ('active', 'archived')", name="chk_user_workout_plans_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    plan_date: Mapped[date | None] = mapped_column(Date)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="workout_plans")
    workout_records: Mapped[list[UserWorkoutRecord]] = relationship(back_populates="plan")


class UserWorkoutRecord(Base, TimestampMixin):
    __tablename__ = "user_workout_records"
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_user_workout_records_user_date"),
        CheckConstraint(
            "completion_status IN ('completed', 'partial', 'skipped')",
            name="chk_user_workout_records_completion_status",
        ),
        CheckConstraint(
            "perceived_exertion IS NULL OR perceived_exertion BETWEEN 1 AND 10",
            name="chk_user_workout_records_perceived_exertion",
        ),
        CheckConstraint(
            "energy_level IS NULL OR energy_level BETWEEN 1 AND 10",
            name="chk_user_workout_records_energy_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_workout_plans.id", ondelete="SET NULL")
    )
    session_name: Mapped[str | None] = mapped_column(String(255))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    completion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    perceived_exertion: Mapped[int | None] = mapped_column(SmallInteger)
    energy_level: Mapped[int | None] = mapped_column(SmallInteger)
    mood: Mapped[str | None] = mapped_column(String(50))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="workout_records")
    plan: Mapped[UserWorkoutPlan | None] = relationship(back_populates="workout_records")
    items: Mapped[list[UserWorkoutRecordItem]] = relationship(
        back_populates="workout_record", cascade="all, delete-orphan"
    )


class UserWorkoutRecordItem(Base, TimestampMixin):
    __tablename__ = "user_workout_record_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_record_id: Mapped[int] = mapped_column(
        ForeignKey("user_workout_records.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sets_count: Mapped[int | None] = mapped_column(Integer)
    reps_text: Mapped[str | None] = mapped_column(String(100))
    weight_text: Mapped[str | None] = mapped_column(String(100))
    duration_text: Mapped[str | None] = mapped_column(String(100))
    distance_text: Mapped[str | None] = mapped_column(String(100))
    raw_text: Mapped[str | None] = mapped_column(Text)
    remark: Mapped[str | None] = mapped_column(Text)

    workout_record: Mapped[UserWorkoutRecord] = relationship(back_populates="items")


class WorkoutRecordDraft(Base, TimestampMixin):
    __tablename__ = "workout_record_drafts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'superseded')",
            name="chk_workout_record_drafts_status",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_workout_record_drafts_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    draft_payload: Mapped[dict | None] = mapped_column(JSON)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    workout_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_workout_records.id", ondelete="SET NULL")
    )
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="workout_record_drafts")
    session: Mapped[ChatSession | None] = relationship()
    workout_record: Mapped[UserWorkoutRecord | None] = relationship()


class UserNutritionRecord(Base, TimestampMixin):
    __tablename__ = "user_nutrition_records"
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_user_nutrition_records_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    calories_estimate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    protein_g_estimate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    carbs_g_estimate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    fat_g_estimate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="nutrition_records")
    conversation_logs: Mapped[list[ConversationLog]] = relationship(
        back_populates="nutrition_record"
    )


class UserBodyStatusRecord(Base, TimestampMixin):
    __tablename__ = "user_body_status_records"
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_user_body_status_records_user_date"),
        CheckConstraint(
            "fatigue_level IS NULL OR fatigue_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_fatigue_level",
        ),
        CheckConstraint(
            "stress_level IS NULL OR stress_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_stress_level",
        ),
        CheckConstraint(
            "soreness_level IS NULL OR soreness_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_soreness_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    fatigue_level: Mapped[int | None] = mapped_column(SmallInteger)
    stress_level: Mapped[int | None] = mapped_column(SmallInteger)
    soreness_level: Mapped[int | None] = mapped_column(SmallInteger)
    body_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    mood: Mapped[str | None] = mapped_column(String(50))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="body_status_records")
    conversation_logs: Mapped[list[ConversationLog]] = relationship(
        back_populates="body_status_record"
    )


class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="chk_conversation_logs_role"),
        CheckConstraint(
            "intent_type IS NULL OR intent_type IN "
            "('plan', 'workout', 'nutrition', 'body_status', 'correction', 'query')",
            name="chk_conversation_logs_intent_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL")
    )
    record_date: Mapped[date | None] = mapped_column(Date)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_type: Mapped[str | None] = mapped_column(String(30))
    related_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_workout_plans.id", ondelete="SET NULL")
    )
    related_workout_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_workout_records.id", ondelete="SET NULL")
    )
    related_nutrition_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_nutrition_records.id", ondelete="SET NULL")
    )
    related_body_status_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_body_status_records.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="conversation_logs")
    session: Mapped[ChatSession | None] = relationship(back_populates="conversation_logs")
    nutrition_record: Mapped[UserNutritionRecord | None] = relationship(
        back_populates="conversation_logs"
    )
    body_status_record: Mapped[UserBodyStatusRecord | None] = relationship(
        back_populates="conversation_logs"
    )


class IntentRecognitionLog(Base):
    __tablename__ = "intent_recognition_logs"
    __table_args__ = (
        CheckConstraint(
            "source IN ('llm', 'keyword', 'fallback')",
            name="chk_intent_recognition_logs_source",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="chk_intent_recognition_logs_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL")
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    final_intent: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    keyword_intent: Mapped[str | None] = mapped_column(String(80))
    keyword_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    matched_keywords: Mapped[list | None] = mapped_column(JSON)
    module_name: Mapped[str | None] = mapped_column(String(100))
    module_status: Mapped[str | None] = mapped_column(String(30))
    db_intent_type: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="intent_recognition_logs")
    session: Mapped[ChatSession | None] = relationship()


class UserDefinedMemory(Base, TimestampMixin):
    __tablename__ = "user_defined_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_category IN "
            "('fitness_preference', 'content_preference', 'conversation_preference', "
            "'diet_preference', 'health_constraint_preference')",
            name="chk_user_defined_memories_category",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="chk_user_defined_memories_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_key: Mapped[str] = mapped_column(String(100), nullable=False)
    memory_category: Mapped[str] = mapped_column(String(50), nullable=False)
    memory_value: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source_conversation_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_logs.id", ondelete="SET NULL")
    )

    user: Mapped[User] = relationship(back_populates="defined_memories")
    source_conversation_log: Mapped[ConversationLog | None] = relationship()


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "thread_id", "session_no", name="uq_chat_sessions_user_thread_no"),
        CheckConstraint("status IN ('active', 'closed', 'archived')", name="chk_chat_sessions_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False)
    session_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="chat_sessions")
    conversation_logs: Mapped[list[ConversationLog]] = relationship(back_populates="session")
    summaries: Mapped[list[ChatSessionSummary]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    derived_memories: Mapped[list[AgentDerivedMemory]] = relationship(back_populates="source_session")


class ChatSessionSummary(Base, TimestampMixin):
    __tablename__ = "chat_session_summaries"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "summary_type", "summary_version", name="uq_chat_session_summaries_version"
        ),
        CheckConstraint(
            "summary_type IN ('running_summary', 'final_summary', 'memory_candidate')",
            name="chk_chat_session_summaries_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    summary_type: Mapped[str] = mapped_column(String(30), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict | list | None] = mapped_column(JSON)
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_message_count: Mapped[int | None] = mapped_column(Integer)

    session: Mapped[ChatSession] = relationship(back_populates="summaries")


class AgentDerivedMemory(Base, TimestampMixin):
    __tablename__ = "agent_derived_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_category IN "
            "('fitness_goal_memory', 'training_pattern_memory', 'exercise_preference_memory', "
            "'body_status_baseline_memory', 'nutrition_pattern_memory', "
            "'conversation_style_memory', 'current_phase_memory', 'adherence_risk_memory')",
            name="chk_agent_derived_memories_category",
        ),
        CheckConstraint("status IN ('active', 'superseded', 'expired')", name="chk_agent_derived_memories_status"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_agent_derived_memories_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_category: Mapped[str] = mapped_column(String(60), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict | list | None] = mapped_column(JSON)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    source_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL")
    )
    source_conversation_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_logs.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="derived_memories")
    source_session: Mapped[ChatSession | None] = relationship(back_populates="derived_memories")
    source_conversation_log: Mapped[ConversationLog | None] = relationship()
