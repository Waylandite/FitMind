"""add memory system v1

Revision ID: 20260610_000002
Revises: 20250609_000001
Create Date: 2026-06-10 00:00:02
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_000002"
down_revision: Union[str, None] = "20250609_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_defined_memories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("memory_key", sa.String(length=100), nullable=False),
        sa.Column("memory_category", sa.String(length=50), nullable=False),
        sa.Column("memory_value", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("source_conversation_log_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_defined_memories_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["source_conversation_log_id"],
            ["conversation_logs.id"],
            ondelete="SET NULL",
            name="fk_user_defined_memories_source_conversation_log_id",
        ),
        sa.CheckConstraint(
            "memory_category IN "
            "('fitness_preference', 'content_preference', 'conversation_preference', "
            "'diet_preference', 'health_constraint_preference')",
            name="chk_user_defined_memories_category",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="chk_user_defined_memories_status"),
    )
    op.create_index(
        "idx_user_defined_memories_user_category_status",
        "user_defined_memories",
        ["user_id", "memory_category", "status"],
        unique=False,
    )
    op.create_index(
        "idx_user_defined_memories_user_key_status",
        "user_defined_memories",
        ["user_id", "memory_key", "status"],
        unique=False,
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("session_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_chat_sessions_user_id"),
        sa.UniqueConstraint("user_id", "thread_id", "session_no", name="uq_chat_sessions_user_thread_no"),
        sa.CheckConstraint("status IN ('active', 'closed', 'archived')", name="chk_chat_sessions_status"),
    )
    op.create_index(
        "idx_chat_sessions_user_status_last_message_at",
        "chat_sessions",
        ["user_id", "status", "last_message_at"],
        unique=False,
    )

    with op.batch_alter_table("conversation_logs") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.BigInteger(), nullable=True))
        batch_op.create_foreign_key(
            "fk_conversation_logs_session_id", "chat_sessions", ["session_id"], ["id"], ondelete="SET NULL"
        )
    op.create_index(
        "idx_conversation_logs_session_created_at",
        "conversation_logs",
        ["session_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "chat_session_summaries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("summary_type", sa.String(length=30), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_payload", sa.JSON(), nullable=True),
        sa.Column("summary_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_message_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], ondelete="CASCADE", name="fk_chat_session_summaries_session_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_chat_session_summaries_user_id"
        ),
        sa.UniqueConstraint(
            "session_id", "summary_type", "summary_version", name="uq_chat_session_summaries_version"
        ),
        sa.CheckConstraint(
            "summary_type IN ('running_summary', 'final_summary', 'memory_candidate')",
            name="chk_chat_session_summaries_type",
        ),
    )
    op.create_index(
        "idx_chat_session_summaries_session_type_version",
        "chat_session_summaries",
        ["session_id", "summary_type", "summary_version"],
        unique=False,
    )

    op.create_table(
        "agent_derived_memories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("memory_category", sa.String(length=60), nullable=False),
        sa.Column("memory_type", sa.String(length=100), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_payload", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("source_session_id", sa.BigInteger(), nullable=True),
        sa.Column("source_conversation_log_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_agent_derived_memories_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["source_session_id"], ["chat_sessions.id"], ondelete="SET NULL", name="fk_agent_derived_memories_source_session_id"
        ),
        sa.ForeignKeyConstraint(
            ["source_conversation_log_id"],
            ["conversation_logs.id"],
            ondelete="SET NULL",
            name="fk_agent_derived_memories_source_conversation_log_id",
        ),
        sa.CheckConstraint(
            "memory_category IN "
            "('fitness_goal_memory', 'training_pattern_memory', 'exercise_preference_memory', "
            "'body_status_baseline_memory', 'nutrition_pattern_memory', "
            "'conversation_style_memory', 'current_phase_memory', 'adherence_risk_memory')",
            name="chk_agent_derived_memories_category",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'expired')", name="chk_agent_derived_memories_status"
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_agent_derived_memories_confidence",
        ),
    )
    op.create_index(
        "idx_agent_derived_memories_user_category_status",
        "agent_derived_memories",
        ["user_id", "memory_category", "status"],
        unique=False,
    )
    op.create_index(
        "idx_agent_derived_memories_user_type_status",
        "agent_derived_memories",
        ["user_id", "memory_type", "status"],
        unique=False,
    )
    op.create_index(
        "idx_agent_derived_memories_source_session_id",
        "agent_derived_memories",
        ["source_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_agent_derived_memories_source_session_id", table_name="agent_derived_memories")
    op.drop_index("idx_agent_derived_memories_user_type_status", table_name="agent_derived_memories")
    op.drop_index("idx_agent_derived_memories_user_category_status", table_name="agent_derived_memories")
    op.drop_table("agent_derived_memories")

    op.drop_index("idx_chat_session_summaries_session_type_version", table_name="chat_session_summaries")
    op.drop_table("chat_session_summaries")

    op.drop_index("idx_conversation_logs_session_created_at", table_name="conversation_logs")
    with op.batch_alter_table("conversation_logs") as batch_op:
        batch_op.drop_constraint("fk_conversation_logs_session_id", type_="foreignkey")
        batch_op.drop_column("session_id")

    op.drop_index("idx_chat_sessions_user_status_last_message_at", table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_index("idx_user_defined_memories_user_key_status", table_name="user_defined_memories")
    op.drop_index("idx_user_defined_memories_user_category_status", table_name="user_defined_memories")
    op.drop_table("user_defined_memories")
