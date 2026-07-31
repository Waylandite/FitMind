"""add persistent intent clarification state

Revision ID: 20260731_000010
Revises: 20260615_000009
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_000010"
down_revision: Union[str, None] = "20260615_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intent_clarifications",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("candidate_intents", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("active_session_key", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("last_question", sa.Text(), nullable=False),
        sa.Column("last_user_reply", sa.Text(), nullable=True),
        sa.Column("resolved_intent", sa.String(length=80), nullable=True),
        sa.Column("resolved_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("resolution_source", sa.String(length=30), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending', 'resolved', 'cancelled', 'expired', 'failed', 'superseded')", name="chk_intent_clarifications_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_intent_clarifications_active", "intent_clarifications", ["user_id", "session_id", "status"], unique=False)


def downgrade() -> None:
    # MySQL may reuse this index for the foreign key; dropping the table
    # removes both safely, whereas dropping the index first raises 1553.
    op.drop_table("intent_clarifications")
