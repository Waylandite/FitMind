"""add intent recognition logs

Revision ID: 20260613_000004
Revises: 20260613_000003
Create Date: 2026-06-13 00:00:04
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_000004"
down_revision: Union[str, None] = "20260613_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intent_recognition_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("final_intent", sa.String(length=80), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("keyword_intent", sa.String(length=80), nullable=True),
        sa.Column("keyword_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("matched_keywords", sa.JSON(), nullable=True),
        sa.Column("module_name", sa.String(length=100), nullable=True),
        sa.Column("module_status", sa.String(length=30), nullable=True),
        sa.Column("db_intent_type", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_intent_recognition_logs_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            ondelete="SET NULL",
            name="fk_intent_recognition_logs_session_id",
        ),
        sa.CheckConstraint(
            "source IN ('llm', 'keyword', 'fallback')",
            name="chk_intent_recognition_logs_source",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="chk_intent_recognition_logs_confidence",
        ),
    )
    op.create_index(
        "idx_intent_recognition_logs_user_created",
        "intent_recognition_logs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_intent_recognition_logs_session",
        "intent_recognition_logs",
        ["session_id", "id"],
        unique=False,
    )
    op.create_index(
        "idx_intent_recognition_logs_final_intent",
        "intent_recognition_logs",
        ["final_intent", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_intent_recognition_logs_final_intent", table_name="intent_recognition_logs")
    op.drop_index("idx_intent_recognition_logs_session", table_name="intent_recognition_logs")
    op.drop_index("idx_intent_recognition_logs_user_created", table_name="intent_recognition_logs")
    op.drop_table("intent_recognition_logs")
