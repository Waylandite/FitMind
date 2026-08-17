"""add auth version and refresh sessions

Revision ID: 20260817_000011
Revises: 20260731_000010
Create Date: 2026-08-17 00:00:11
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260817_000011"
down_revision: Union[str, None] = "20260731_000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.BigInteger(), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"], ["auth_refresh_sessions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("token_hash", name="uq_auth_refresh_sessions_token_hash"),
    )
    op.create_index(
        "ix_auth_refresh_sessions_user_id", "auth_refresh_sessions", ["user_id"]
    )
    op.create_index(
        "ix_auth_refresh_sessions_family_id", "auth_refresh_sessions", ["family_id"]
    )
    op.create_index(
        "ix_auth_refresh_sessions_expires_at", "auth_refresh_sessions", ["expires_at"]
    )
    op.create_index(
        "ix_auth_refresh_sessions_revoked_at", "auth_refresh_sessions", ["revoked_at"]
    )


def downgrade() -> None:
    op.drop_table("auth_refresh_sessions")
    op.drop_column("users", "auth_version")
