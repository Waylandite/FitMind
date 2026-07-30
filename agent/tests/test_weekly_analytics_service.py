from datetime import date
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.repositories.nutrition import BodyStatusRecordRepository
from fitmind_agent.repositories.nutrition import NutritionRecordRepository
from fitmind_agent.repositories.workout import WorkoutRecordRepository
from fitmind_agent.services import weekly_analytics_service
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsQueryError
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsService
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsValidationError


def test_current_week_compares_same_number_of_days() -> None:
    service = WeeklyAnalyticsService()
    wednesday = date(2026, 7, 29)

    period = service.build_period(anchor_date=wednesday, today=wednesday)

    assert period.current.start_date == date(2026, 7, 27)
    assert period.current.end_date == wednesday
    assert period.previous.start_date == date(2026, 7, 20)
    assert period.previous.end_date == date(2026, 7, 22)
    assert period.current.day_count == 3
    assert period.is_current_week is True


def test_historical_week_uses_complete_natural_weeks() -> None:
    service = WeeklyAnalyticsService()

    period = service.build_period(
        anchor_date=date(2026, 7, 15),
        today=date(2026, 7, 30),
    )

    assert period.current.start_date == date(2026, 7, 13)
    assert period.current.end_date == date(2026, 7, 19)
    assert period.previous.start_date == date(2026, 7, 6)
    assert period.previous.end_date == date(2026, 7, 12)
    assert period.current.day_count == 7
    assert period.is_current_week is False


def test_future_anchor_is_rejected() -> None:
    with pytest.raises(WeeklyAnalyticsValidationError, match="未来周"):
        WeeklyAnalyticsService().build_period(
            anchor_date=date(2026, 8, 1),
            today=date(2026, 7, 30),
        )


def test_weekly_analytics_aggregates_real_records_without_filling_missing_days(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'weekly.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(weekly_analytics_service, "SessionLocal", test_session_local)

    active_monday = date.today() - timedelta(days=date.today().weekday())
    current_start = active_monday - timedelta(days=7)
    previous_start = current_start - timedelta(days=7)
    anchor = current_start + timedelta(days=2)

    with test_session_local() as session:
        user = User(email="weekly@example.com", username="weekly_user", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)
        workout_repo = WorkoutRecordRepository(session)

        chest = workout_repo.create_record(
            user_id=user.id,
            record_date=current_start,
            session_name="胸部训练",
            duration_minutes=45,
            raw_text="卧推 4 组",
        )
        workout_repo.replace_items(
            workout_record_id=chest.id,
            items=[
                {
                    "exercise_name": "卧推",
                    "exercise_type": "strength",
                    "sets_count": 4,
                }
            ],
        )
        cardio = workout_repo.create_record(
            user_id=user.id,
            record_date=current_start,
            session_name="晚间有氧",
            duration_minutes=20,
            raw_text="跑步 20 分钟",
        )
        workout_repo.replace_items(
            workout_record_id=cardio.id,
            items=[
                {
                    "exercise_name": "跑步",
                    "exercise_type": "cardio",
                    "duration_text": "20分钟",
                }
            ],
        )
        legs = workout_repo.create_record(
            user_id=user.id,
            record_date=current_start + timedelta(days=1),
            session_name="腿部训练",
            raw_text="深蹲 3 组",
        )
        workout_repo.replace_items(
            workout_record_id=legs.id,
            items=[
                {
                    "exercise_name": "深蹲",
                    "exercise_type": "strength",
                    "sets_count": 3,
                }
            ],
        )
        previous = workout_repo.create_record(
            user_id=user.id,
            record_date=previous_start,
            session_name="胸部训练",
            duration_minutes=40,
            raw_text="卧推 2 组",
        )
        workout_repo.replace_items(
            workout_record_id=previous.id,
            items=[
                {
                    "exercise_name": "卧推",
                    "exercise_type": "strength",
                    "sets_count": 2,
                }
            ],
        )

        nutrition_repo = NutritionRecordRepository(session)
        nutrition_repo.upsert_daily_record(
            user_id=user.id,
            record_date=current_start,
            raw_text="周一饮食",
            calories_estimate=Decimal("2000"),
            protein_g_estimate=Decimal("100"),
        )
        nutrition_repo.upsert_daily_record(
            user_id=user.id,
            record_date=current_start + timedelta(days=1),
            raw_text="周二饮食",
            calories_estimate=Decimal("2200"),
            protein_g_estimate=Decimal("120"),
        )
        nutrition_repo.upsert_daily_record(
            user_id=user.id,
            record_date=previous_start,
            raw_text="上周饮食",
            calories_estimate=Decimal("1800"),
            protein_g_estimate=Decimal("90"),
        )

        body_repo = BodyStatusRecordRepository(session)
        body_repo.upsert_daily_record(
            user_id=user.id,
            record_date=current_start,
            raw_text="睡眠 7 小时",
            sleep_hours=Decimal("7"),
            fatigue_level=3,
            body_weight_kg=Decimal("70"),
        )
        body_repo.upsert_daily_record(
            user_id=user.id,
            record_date=current_start + timedelta(days=4),
            raw_text="睡眠 8 小时",
            sleep_hours=Decimal("8"),
            fatigue_level=2,
            body_weight_kg=Decimal("69.5"),
        )
        body_repo.upsert_daily_record(
            user_id=user.id,
            record_date=previous_start,
            raw_text="上周身体状态",
            sleep_hours=Decimal("6.5"),
            body_weight_kg=Decimal("70.2"),
        )
        user_id = user.id

    response = WeeklyAnalyticsService().analyze(user_id=user_id, anchor_date=anchor)

    assert response.training.current.record_count == 3
    assert response.training.current.training_day_count == 2
    assert response.training.current.strength_sets_count == 7
    assert response.training.current.cardio_item_count == 1
    assert response.training.changes["record_count"].delta == 2
    assert response.nutrition.current.record_days == 2
    assert response.nutrition.current.average_calories == 2100
    assert response.recovery.current.average_sleep_hours == 7.5
    assert response.recovery.current.body_weight_change_kg == -0.5
    assert response.recovery.previous.body_weight_change_kg is None
    assert response.daily_series[0].current.workout_records == 2
    assert response.daily_series[2].current.workout_records == 0
    assert response.daily_series[2].current.calories is None
    groups = {item.muscle_group: item for item in response.muscle_distribution}
    assert groups["chest"].current_count == 1
    assert groups["cardio"].current_count == 1
    assert groups["legs"].current_count == 1


def test_zero_previous_value_has_no_percentage_change() -> None:
    comparison = WeeklyAnalyticsService._compare_values(3, 0)

    assert comparison.delta == 3
    assert comparison.delta_percent is None


def test_database_query_failure_is_not_reported_as_empty_data(monkeypatch) -> None:
    def fail_query(**kwargs):
        del kwargs
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(WeeklyAnalyticsService, "_query_workouts", staticmethod(fail_query))

    with pytest.raises(WeeklyAnalyticsQueryError, match="database unavailable"):
        WeeklyAnalyticsService().analyze(user_id=1)
