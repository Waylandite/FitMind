"""allow multiple workout records per day

Revision ID: 20260615_000009
Revises: 20260615_000008
Create Date: 2026-06-15 00:00:09
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260615_000009"
down_revision: Union[str, None] = "20260615_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_user_workout_records_user_id",
        "user_workout_records",
        ["user_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_user_workout_records_user_date",
        "user_workout_records",
        type_="unique",
    )
    op.add_column(
        "user_workout_record_items",
        sa.Column("exercise_type", sa.String(length=20), nullable=False, server_default="strength"),
    )
    op.create_check_constraint(
        "chk_user_workout_record_items_exercise_type",
        "user_workout_record_items",
        "exercise_type IN ('strength', 'cardio', 'mobility', 'other')",
    )
    op.create_index(
        "idx_user_workout_records_user_date",
        "user_workout_records",
        ["user_id", "record_date", "id"],
        unique=False,
    )
    op.create_index(
        "idx_user_workout_record_items_type",
        "user_workout_record_items",
        ["exercise_type", "workout_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_user_workout_record_items_type", table_name="user_workout_record_items")
    op.drop_index("idx_user_workout_records_user_date", table_name="user_workout_records")
    op.drop_constraint(
        "chk_user_workout_record_items_exercise_type",
        "user_workout_record_items",
        type_="check",
    )
    op.drop_column("user_workout_record_items", "exercise_type")
    op.execute(
        """
        DELETE r1 FROM user_workout_records r1
        JOIN user_workout_records r2
          ON r1.user_id = r2.user_id
         AND r1.record_date = r2.record_date
         AND r1.id < r2.id
        """
    )
    op.create_unique_constraint(
        "uq_user_workout_records_user_date",
        "user_workout_records",
        ["user_id", "record_date"],
    )
    op.drop_index("idx_user_workout_records_user_id", table_name="user_workout_records")
