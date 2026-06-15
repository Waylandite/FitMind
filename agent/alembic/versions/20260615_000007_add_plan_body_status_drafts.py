"""add workout plan and body status drafts

Revision ID: 20260615_000007
Revises: 20260614_000006
Create Date: 2026-06-15 00:00:07
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_000007"
down_revision: Union[str, None] = "20260614_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_draft_table(table_name: str, record_fk_name: str, record_table: str) -> None:
    op.create_table(
        table_name,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("draft_payload", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(record_fk_name, sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint([record_fk_name], [f"{record_table}.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'superseded')",
            name=f"chk_{table_name}_status",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name=f"chk_{table_name}_confidence",
        ),
    )
    op.create_index(
        f"idx_{table_name}_session_status",
        table_name,
        ["session_id", "status", "id"],
        unique=False,
    )
    op.create_index(
        f"idx_{table_name}_user_status",
        table_name,
        ["user_id", "status", "id"],
        unique=False,
    )


def upgrade() -> None:
    _create_draft_table("workout_plan_drafts", "workout_plan_id", "user_workout_plans")
    _create_draft_table("body_status_record_drafts", "body_status_record_id", "user_body_status_records")


def downgrade() -> None:
    op.drop_index("idx_body_status_record_drafts_user_status", table_name="body_status_record_drafts")
    op.drop_index("idx_body_status_record_drafts_session_status", table_name="body_status_record_drafts")
    op.drop_table("body_status_record_drafts")
    op.drop_index("idx_workout_plan_drafts_user_status", table_name="workout_plan_drafts")
    op.drop_index("idx_workout_plan_drafts_session_status", table_name="workout_plan_drafts")
    op.drop_table("workout_plan_drafts")
