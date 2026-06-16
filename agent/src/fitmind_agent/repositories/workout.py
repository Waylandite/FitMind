from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from fitmind_agent.db.models import UserWorkoutRecord
from fitmind_agent.db.models import UserWorkoutRecordItem
from fitmind_agent.db.models import UserWorkoutPlan
from fitmind_agent.db.models import WorkoutPlanDraft
from fitmind_agent.db.models import WorkoutRecordDraft


class WorkoutRecordDraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> WorkoutRecordDraft:
        draft = WorkoutRecordDraft(**dict(data))
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def get_by_id(self, draft_id: int) -> WorkoutRecordDraft | None:
        return self.session.get(WorkoutRecordDraft, draft_id)

    def get_latest_pending(self, user_id: int, session_id: int | None) -> WorkoutRecordDraft | None:
        stmt = (
            select(WorkoutRecordDraft)
            .where(
                WorkoutRecordDraft.user_id == user_id,
                WorkoutRecordDraft.status == "pending",
            )
            .order_by(WorkoutRecordDraft.id.desc())
            .limit(1)
        )
        if session_id is None:
            stmt = stmt.where(WorkoutRecordDraft.session_id.is_(None))
        else:
            stmt = stmt.where(WorkoutRecordDraft.session_id == session_id)

        return self.session.scalar(stmt)

    def update(self, draft: WorkoutRecordDraft, data: Mapping[str, Any]) -> WorkoutRecordDraft:
        for key, value in data.items():
            setattr(draft, key, value)
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft


class WorkoutPlanDraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, Any]) -> WorkoutPlanDraft:
        draft = WorkoutPlanDraft(**dict(data))
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def get_latest_pending(self, user_id: int, session_id: int | None) -> WorkoutPlanDraft | None:
        stmt = (
            select(WorkoutPlanDraft)
            .where(
                WorkoutPlanDraft.user_id == user_id,
                WorkoutPlanDraft.status == "pending",
            )
            .order_by(WorkoutPlanDraft.id.desc())
            .limit(1)
        )
        if session_id is None:
            stmt = stmt.where(WorkoutPlanDraft.session_id.is_(None))
        else:
            stmt = stmt.where(WorkoutPlanDraft.session_id == session_id)
        return self.session.scalar(stmt)

    def update(self, draft: WorkoutPlanDraft, data: Mapping[str, Any]) -> WorkoutPlanDraft:
        for key, value in data.items():
            setattr(draft, key, value)
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft


class WorkoutPlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_plan(
        self,
        *,
        user_id: int,
        title: str | None,
        plan_date: date | None,
        raw_text: str,
        source: str = "manual",
        status: str = "active",
        remark: str | None = None,
    ) -> UserWorkoutPlan:
        plan = UserWorkoutPlan(
            user_id=user_id,
            title=title,
            plan_date=plan_date,
            raw_text=raw_text,
            source=source,
            status=status,
            remark=remark,
        )
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def list_active_plans(self, *, user_id: int, limit: int = 5) -> list[UserWorkoutPlan]:
        stmt = (
            select(UserWorkoutPlan)
            .where(UserWorkoutPlan.user_id == user_id, UserWorkoutPlan.status == "active")
            .order_by(UserWorkoutPlan.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def get_latest_plan(self, *, user_id: int) -> UserWorkoutPlan | None:
        stmt = (
            select(UserWorkoutPlan)
            .where(UserWorkoutPlan.user_id == user_id)
            .order_by(UserWorkoutPlan.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class WorkoutRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_record(
        self,
        *,
        user_id: int,
        record_date: date,
        raw_text: str,
        session_name: str | None = None,
        duration_minutes: int | None = None,
        completion_status: str = "completed",
        perceived_exertion: int | None = None,
        energy_level: int | None = None,
        mood: str | None = None,
    ) -> UserWorkoutRecord:
        record = UserWorkoutRecord(
            user_id=user_id,
            record_date=record_date,
            session_name=session_name,
            duration_minutes=duration_minutes,
            completion_status=completion_status,
            perceived_exertion=perceived_exertion,
            energy_level=energy_level,
            mood=mood,
            raw_text=raw_text,
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_by_user_date(self, *, user_id: int, record_date: date) -> list[UserWorkoutRecord]:
        stmt = (
            select(UserWorkoutRecord)
            .where(
                UserWorkoutRecord.user_id == user_id,
                UserWorkoutRecord.record_date == record_date,
            )
            .order_by(UserWorkoutRecord.id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_between_dates(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[UserWorkoutRecord]:
        stmt = (
            select(UserWorkoutRecord)
            .options(joinedload(UserWorkoutRecord.items))
            .where(
                UserWorkoutRecord.user_id == user_id,
                UserWorkoutRecord.record_date >= start_date,
                UserWorkoutRecord.record_date <= end_date,
            )
            .order_by(UserWorkoutRecord.record_date.asc(), UserWorkoutRecord.id.asc())
        )
        return list(self.session.scalars(stmt).unique())

    def replace_items(
        self,
        *,
        workout_record_id: int,
        items: list[Mapping[str, Any]],
    ) -> list[UserWorkoutRecordItem]:
        existing = list(
            self.session.scalars(
                select(UserWorkoutRecordItem).where(
                    UserWorkoutRecordItem.workout_record_id == workout_record_id
                )
            )
        )
        for item in existing:
            self.session.delete(item)

        created: list[UserWorkoutRecordItem] = []
        for index, item in enumerate(items, start=1):
            record_item = UserWorkoutRecordItem(
                workout_record_id=workout_record_id,
                sequence_no=index,
                exercise_name=str(item.get("exercise_name") or "").strip(),
                sets_count=item.get("sets_count"),
                exercise_type=str(item.get("exercise_type") or "strength"),
                reps_text=item.get("reps_text"),
                weight_text=item.get("weight_text"),
                duration_text=item.get("duration_text"),
                distance_text=item.get("distance_text"),
                raw_text=item.get("raw_text"),
                remark=item.get("remark"),
            )
            self.session.add(record_item)
            created.append(record_item)

        self.session.commit()
        for item in created:
            self.session.refresh(item)

        return created
