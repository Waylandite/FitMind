"""init fitmind v1

Revision ID: 20250609_000001
Revises:
Create Date: 2026-06-09 00:00:01
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20250609_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="chk_users_status"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("target_weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("goal_type", sa.String(length=50), nullable=True),
        sa.Column("training_level", sa.String(length=50), nullable=True),
        sa.Column("injury_notes", sa.Text(), nullable=True),
        sa.Column("medical_notes", sa.Text(), nullable=True),
        sa.Column("diet_preference", sa.Text(), nullable=True),
        sa.Column("preferred_training_days", sa.Text(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_profiles_user_id"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    op.create_table(
        "user_workout_plans",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("plan_date", sa.Date(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_workout_plans_user_id"
        ),
        sa.CheckConstraint("source IN ('manual', 'agent')", name="chk_user_workout_plans_source"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="chk_user_workout_plans_status"),
    )
    op.create_index(
        "idx_user_workout_plans_user_date", "user_workout_plans", ["user_id", "plan_date"], unique=False
    )

    op.create_table(
        "user_workout_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=True),
        sa.Column("session_name", sa.String(length=255), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("completion_status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("perceived_exertion", sa.SmallInteger(), nullable=True),
        sa.Column("energy_level", sa.SmallInteger(), nullable=True),
        sa.Column("mood", sa.String(length=50), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_workout_records_user_id"),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["user_workout_plans.id"], ondelete="SET NULL", name="fk_user_workout_records_plan_id"
        ),
        sa.UniqueConstraint("user_id", "record_date", name="uq_user_workout_records_user_date"),
        sa.CheckConstraint(
            "completion_status IN ('completed', 'partial', 'skipped')",
            name="chk_user_workout_records_completion_status",
        ),
        sa.CheckConstraint(
            "perceived_exertion IS NULL OR perceived_exertion BETWEEN 1 AND 10",
            name="chk_user_workout_records_perceived_exertion",
        ),
        sa.CheckConstraint(
            "energy_level IS NULL OR energy_level BETWEEN 1 AND 10",
            name="chk_user_workout_records_energy_level",
        ),
    )
    op.create_index("idx_user_workout_records_plan_id", "user_workout_records", ["plan_id"], unique=False)

    op.create_table(
        "user_workout_record_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("workout_record_id", sa.BigInteger(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("exercise_name", sa.String(length=255), nullable=False),
        sa.Column("sets_count", sa.Integer(), nullable=True),
        sa.Column("reps_text", sa.String(length=100), nullable=True),
        sa.Column("weight_text", sa.String(length=100), nullable=True),
        sa.Column("duration_text", sa.String(length=100), nullable=True),
        sa.Column("distance_text", sa.String(length=100), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["workout_record_id"],
            ["user_workout_records.id"],
            ondelete="CASCADE",
            name="fk_user_workout_record_items_record_id",
        ),
    )
    op.create_index(
        "idx_user_workout_record_items_record_sequence",
        "user_workout_record_items",
        ["workout_record_id", "sequence_no"],
        unique=False,
    )

    op.create_table(
        "user_nutrition_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("calories_estimate", sa.Numeric(8, 2), nullable=True),
        sa.Column("protein_g_estimate", sa.Numeric(8, 2), nullable=True),
        sa.Column("carbs_g_estimate", sa.Numeric(8, 2), nullable=True),
        sa.Column("fat_g_estimate", sa.Numeric(8, 2), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_nutrition_records_user_id"
        ),
        sa.UniqueConstraint("user_id", "record_date", name="uq_user_nutrition_records_user_date"),
    )

    op.create_table(
        "user_body_status_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("sleep_hours", sa.Numeric(4, 2), nullable=True),
        sa.Column("fatigue_level", sa.SmallInteger(), nullable=True),
        sa.Column("stress_level", sa.SmallInteger(), nullable=True),
        sa.Column("soreness_level", sa.SmallInteger(), nullable=True),
        sa.Column("body_weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("mood", sa.String(length=50), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_body_status_records_user_id"
        ),
        sa.UniqueConstraint("user_id", "record_date", name="uq_user_body_status_records_user_date"),
        sa.CheckConstraint(
            "fatigue_level IS NULL OR fatigue_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_fatigue_level",
        ),
        sa.CheckConstraint(
            "stress_level IS NULL OR stress_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_stress_level",
        ),
        sa.CheckConstraint(
            "soreness_level IS NULL OR soreness_level BETWEEN 1 AND 10",
            name="chk_user_body_status_records_soreness_level",
        ),
    )

    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("intent_type", sa.String(length=30), nullable=True),
        sa.Column("related_plan_id", sa.BigInteger(), nullable=True),
        sa.Column("related_workout_record_id", sa.BigInteger(), nullable=True),
        sa.Column("related_nutrition_record_id", sa.BigInteger(), nullable=True),
        sa.Column("related_body_status_record_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_conversation_logs_user_id"),
        sa.ForeignKeyConstraint(
            ["related_plan_id"],
            ["user_workout_plans.id"],
            ondelete="SET NULL",
            name="fk_conversation_logs_related_plan_id",
        ),
        sa.ForeignKeyConstraint(
            ["related_workout_record_id"],
            ["user_workout_records.id"],
            ondelete="SET NULL",
            name="fk_conversation_logs_related_workout_record_id",
        ),
        sa.ForeignKeyConstraint(
            ["related_nutrition_record_id"],
            ["user_nutrition_records.id"],
            ondelete="SET NULL",
            name="fk_conversation_logs_related_nutrition_record_id",
        ),
        sa.ForeignKeyConstraint(
            ["related_body_status_record_id"],
            ["user_body_status_records.id"],
            ondelete="SET NULL",
            name="fk_conversation_logs_related_body_status_record_id",
        ),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="chk_conversation_logs_role"),
        sa.CheckConstraint(
            "intent_type IS NULL OR intent_type IN "
            "('plan', 'workout', 'nutrition', 'body_status', 'correction', 'query')",
            name="chk_conversation_logs_intent_type",
        ),
    )
    op.create_index(
        "idx_conversation_logs_user_record_date", "conversation_logs", ["user_id", "record_date"], unique=False
    )
    op.create_index(
        "idx_conversation_logs_thread_created_at",
        "conversation_logs",
        ["thread_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_conversation_logs_thread_created_at", table_name="conversation_logs")
    op.drop_index("idx_conversation_logs_user_record_date", table_name="conversation_logs")
    op.drop_table("conversation_logs")

    op.drop_table("user_body_status_records")
    op.drop_table("user_nutrition_records")

    op.drop_index("idx_user_workout_record_items_record_sequence", table_name="user_workout_record_items")
    op.drop_table("user_workout_record_items")

    op.drop_index("idx_user_workout_records_plan_id", table_name="user_workout_records")
    op.drop_table("user_workout_records")

    op.drop_index("idx_user_workout_plans_user_date", table_name="user_workout_plans")
    op.drop_table("user_workout_plans")

    op.drop_table("user_profiles")
    op.drop_table("users")
