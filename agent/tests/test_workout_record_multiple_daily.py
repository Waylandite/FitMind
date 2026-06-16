from datetime import date

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.db.models import UserWorkoutRecord
from fitmind_agent.db.models import UserWorkoutRecordItem
from fitmind_agent.repositories.workout import WorkoutRecordRepository


def test_workout_records_allow_multiple_sessions_per_day() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="workout@example.com", username="workout_user", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        repo = WorkoutRecordRepository(session)
        record_date = date(2026, 6, 15)

        strength_record = repo.create_record(
            user_id=user.id,
            record_date=record_date,
            session_name="胸部训练",
            raw_text="卧推 5 组",
        )
        repo.replace_items(
            workout_record_id=strength_record.id,
            items=[
                {
                    "exercise_name": "卧推",
                    "exercise_type": "strength",
                    "sets_count": 5,
                    "reps_text": "8次",
                    "weight_text": "80kg",
                }
            ],
        )

        cardio_record = repo.create_record(
            user_id=user.id,
            record_date=record_date,
            session_name="晚间有氧",
            raw_text="跑步 30 分钟",
        )
        repo.replace_items(
            workout_record_id=cardio_record.id,
            items=[
                {
                    "exercise_name": "跑步",
                    "exercise_type": "cardio",
                    "duration_text": "30分钟",
                    "distance_text": "5km",
                }
            ],
        )

        records = list(
            session.scalars(
                select(UserWorkoutRecord)
                .where(UserWorkoutRecord.user_id == user.id)
                .order_by(UserWorkoutRecord.id.asc())
            )
        )
        items = list(
            session.scalars(
                select(UserWorkoutRecordItem)
                .where(UserWorkoutRecordItem.workout_record_id.in_([record.id for record in records]))
                .order_by(UserWorkoutRecordItem.id.asc())
            )
        )

        assert len(records) == 2
        assert records[0].session_name == "胸部训练"
        assert records[1].session_name == "晚间有氧"
        assert len(items) == 2
        assert items[0].workout_record_id == records[0].id
        assert items[0].exercise_type == "strength"
        assert items[1].workout_record_id == records[1].id
        assert items[1].exercise_type == "cardio"
