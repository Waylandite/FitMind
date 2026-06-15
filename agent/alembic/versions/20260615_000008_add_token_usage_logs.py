"""add token usage logs

Revision ID: 20260615_000008
Revises: 20260615_000007
Create Date: 2026-06-15 00:00:08
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_000008"
down_revision: Union[str, None] = "20260615_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("thread_id", sa.String(length=100), nullable=True),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("workflow", sa.String(length=80), nullable=True),
        sa.Column("node_name", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="deepseek"),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("is_stream", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("usage_source", sa.String(length=30), nullable=False, server_default="provider"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_usage", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "usage_source IN ('provider', 'estimated', 'unavailable')",
            name="chk_llm_call_logs_usage_source",
        ),
    )
    op.create_index("idx_llm_call_logs_request", "llm_call_logs", ["request_id", "id"], unique=False)
    op.create_index("idx_llm_call_logs_session", "llm_call_logs", ["session_id", "created_at"], unique=False)
    op.create_index("idx_llm_call_logs_user_created", "llm_call_logs", ["user_id", "created_at"], unique=False)
    op.create_index("idx_llm_call_logs_model_created", "llm_call_logs", ["model", "created_at"], unique=False)

    op.create_table(
        "chat_turn_token_usage",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("thread_id", sa.String(length=100), nullable=True),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("intent_type", sa.String(length=80), nullable=True),
        sa.Column("total_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_breakdown", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("request_id", name="uq_chat_turn_token_usage_request_id"),
    )
    op.create_index("idx_chat_turn_token_usage_session", "chat_turn_token_usage", ["session_id", "created_at"], unique=False)
    op.create_index("idx_chat_turn_token_usage_user_created", "chat_turn_token_usage", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_chat_turn_token_usage_user_created", table_name="chat_turn_token_usage")
    op.drop_index("idx_chat_turn_token_usage_session", table_name="chat_turn_token_usage")
    op.drop_table("chat_turn_token_usage")
    op.drop_index("idx_llm_call_logs_model_created", table_name="llm_call_logs")
    op.drop_index("idx_llm_call_logs_user_created", table_name="llm_call_logs")
    op.drop_index("idx_llm_call_logs_session", table_name="llm_call_logs")
    op.drop_index("idx_llm_call_logs_request", table_name="llm_call_logs")
    op.drop_table("llm_call_logs")
