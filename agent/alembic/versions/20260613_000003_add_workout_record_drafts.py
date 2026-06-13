"""add workout record drafts

Revision ID: 20260613_000003
Revises: 20260610_000002
Create Date: 2026-06-13 00:00:03
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_000003"
down_revision: Union[str, None] = "20260610_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workout_record_drafts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("draft_payload", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workout_record_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_workout_record_drafts_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            ondelete="SET NULL",
            name="fk_workout_record_drafts_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["workout_record_id"],
            ["user_workout_records.id"],
            ondelete="SET NULL",
            name="fk_workout_record_drafts_workout_record_id",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'superseded')",
            name="chk_workout_record_drafts_status",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_workout_record_drafts_confidence",
        ),
    )
    op.create_index(
        "idx_workout_record_drafts_session_status",
        "workout_record_drafts",
        ["session_id", "status", "id"],
        unique=False,
    )
    op.create_index(
        "idx_workout_record_drafts_user_status",
        "workout_record_drafts",
        ["user_id", "status", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_workout_record_drafts_user_status", table_name="workout_record_drafts")
    op.drop_index("idx_workout_record_drafts_session_status", table_name="workout_record_drafts")
    op.drop_table("workout_record_drafts")
