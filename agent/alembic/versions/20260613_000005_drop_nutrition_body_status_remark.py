"""drop nutrition and body status remark columns

Revision ID: 20260613_000005
Revises: 20260613_000004
Create Date: 2026-06-13 00:00:05
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_000005"
down_revision: Union[str, None] = "20260613_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("user_nutrition_records", "remark")
    op.drop_column("user_body_status_records", "remark")


def downgrade() -> None:
    op.add_column("user_body_status_records", sa.Column("remark", sa.Text(), nullable=True))
    op.add_column("user_nutrition_records", sa.Column("remark", sa.Text(), nullable=True))
