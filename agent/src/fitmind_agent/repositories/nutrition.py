from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import BodyStatusRecordDraft
from fitmind_agent.db.models import NutritionRecordDraft
from fitmind_agent.db.models import UserBodyStatusRecord
from fitmind_agent.db.models import UserNutritionRecord


class NutritionRecordDraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data) -> NutritionRecordDraft:
        draft = NutritionRecordDraft(**dict(data))
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def get_latest_pending(
        self,
        *,
        user_id: int,
        session_id: int | None,
    ) -> NutritionRecordDraft | None:
        stmt = (
            select(NutritionRecordDraft)
            .where(
                NutritionRecordDraft.user_id == user_id,
                NutritionRecordDraft.status == "pending",
            )
            .order_by(NutritionRecordDraft.id.desc())
            .limit(1)
        )
        if session_id is None:
            stmt = stmt.where(NutritionRecordDraft.session_id.is_(None))
        else:
            stmt = stmt.where(NutritionRecordDraft.session_id == session_id)
        return self.session.scalar(stmt)

    def update(self, draft: NutritionRecordDraft, data) -> NutritionRecordDraft:
        for key, value in dict(data).items():
            setattr(draft, key, value)
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft


class BodyStatusRecordDraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data) -> BodyStatusRecordDraft:
        draft = BodyStatusRecordDraft(**dict(data))
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft

    def get_latest_pending(
        self,
        *,
        user_id: int,
        session_id: int | None,
    ) -> BodyStatusRecordDraft | None:
        stmt = (
            select(BodyStatusRecordDraft)
            .where(
                BodyStatusRecordDraft.user_id == user_id,
                BodyStatusRecordDraft.status == "pending",
            )
            .order_by(BodyStatusRecordDraft.id.desc())
            .limit(1)
        )
        if session_id is None:
            stmt = stmt.where(BodyStatusRecordDraft.session_id.is_(None))
        else:
            stmt = stmt.where(BodyStatusRecordDraft.session_id == session_id)
        return self.session.scalar(stmt)

    def update(self, draft: BodyStatusRecordDraft, data) -> BodyStatusRecordDraft:
        for key, value in dict(data).items():
            setattr(draft, key, value)
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return draft


class NutritionRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_daily_record(
        self,
        *,
        user_id: int,
        record_date: date,
        raw_text: str,
        calories_estimate=None,
        protein_g_estimate=None,
        carbs_g_estimate=None,
        fat_g_estimate=None,
    ) -> UserNutritionRecord:
        record = self.get_by_user_date(user_id=user_id, record_date=record_date)
        next_calories = self._add_optional(
            None if record is None else record.calories_estimate,
            calories_estimate,
        )
        next_protein = self._add_optional(
            None if record is None else record.protein_g_estimate,
            protein_g_estimate,
        )
        next_carbs = self._add_optional(
            None if record is None else record.carbs_g_estimate,
            carbs_g_estimate,
        )
        next_fat = self._add_optional(
            None if record is None else record.fat_g_estimate,
            fat_g_estimate,
        )
        formatted_raw_text = self._format_raw_text_entry(
            raw_text,
            calories_estimate=next_calories,
            protein_g_estimate=next_protein,
        )

        if record is None:
            record = UserNutritionRecord(
                user_id=user_id,
                record_date=record_date,
                raw_text=formatted_raw_text,
                calories_estimate=next_calories,
                protein_g_estimate=next_protein,
                carbs_g_estimate=next_carbs,
                fat_g_estimate=next_fat,
            )
        else:
            record.raw_text = self._append_raw_text(record.raw_text, formatted_raw_text)
            record.calories_estimate = next_calories
            record.protein_g_estimate = next_protein
            record.carbs_g_estimate = next_carbs
            record.fat_g_estimate = next_fat

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_user_date(self, *, user_id: int, record_date: date) -> UserNutritionRecord | None:
        stmt = (
            select(UserNutritionRecord)
            .where(
                UserNutritionRecord.user_id == user_id,
                UserNutritionRecord.record_date == record_date,
            )
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_between_dates(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[UserNutritionRecord]:
        stmt = (
            select(UserNutritionRecord)
            .where(
                UserNutritionRecord.user_id == user_id,
                UserNutritionRecord.record_date >= start_date,
                UserNutritionRecord.record_date <= end_date,
            )
            .order_by(UserNutritionRecord.record_date.asc())
        )
        return list(self.session.scalars(stmt))

    @staticmethod
    def _append_raw_text(existing_text: str | None, new_text: str) -> str:
        normalized_existing = (existing_text or "").strip()
        normalized_new = new_text.strip()
        if not normalized_existing:
            return normalized_new
        if not normalized_new:
            return normalized_existing

        return f"{normalized_existing}\n{normalized_new}"

    @staticmethod
    def _format_raw_text_entry(
        raw_text: str,
        *,
        calories_estimate=None,
        protein_g_estimate=None,
    ) -> str:
        normalized_text = raw_text.strip()
        if not normalized_text:
            return ""
        current_time = datetime.now().strftime("%H:%M")
        cumulative_parts = []
        if protein_g_estimate is not None:
            cumulative_parts.append(
                f"今日累计蛋白约{NutritionRecordRepository._format_decimal(protein_g_estimate)}g"
            )
        if calories_estimate is not None:
            cumulative_parts.append(
                f"热量约{NutritionRecordRepository._format_decimal(calories_estimate)}kcal"
            )
        if cumulative_parts:
            return f"[{current_time}] {normalized_text}，{'，'.join(cumulative_parts)}"
        return f"[{current_time}] {normalized_text}"

    @staticmethod
    def _add_optional(existing, increment):
        if existing is None and increment is None:
            return None
        return Decimal(str(existing or 0)) + Decimal(str(increment or 0))

    @staticmethod
    def _format_decimal(value) -> str:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
        return format(decimal_value.normalize(), "f")


class BodyStatusRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_daily_record(
        self,
        *,
        user_id: int,
        record_date: date,
        raw_text: str,
        sleep_hours=None,
        fatigue_level: int | None = None,
        stress_level: int | None = None,
        soreness_level: int | None = None,
        body_weight_kg=None,
        mood: str | None = None,
    ) -> UserBodyStatusRecord:
        record = self.get_by_user_date(user_id=user_id, record_date=record_date)
        data = {
            "raw_text": self._format_raw_text_entry(raw_text),
            "sleep_hours": sleep_hours,
            "fatigue_level": fatigue_level,
            "stress_level": stress_level,
            "soreness_level": soreness_level,
            "body_weight_kg": body_weight_kg,
            "mood": mood,
        }

        if record is None:
            record = UserBodyStatusRecord(user_id=user_id, record_date=record_date, **data)
        else:
            record.raw_text = self._append_raw_text(record.raw_text, raw_text)
            if sleep_hours is not None:
                record.sleep_hours = sleep_hours
            if fatigue_level is not None:
                record.fatigue_level = fatigue_level
            if stress_level is not None:
                record.stress_level = stress_level
            if soreness_level is not None:
                record.soreness_level = soreness_level
            if body_weight_kg is not None:
                record.body_weight_kg = body_weight_kg
            if mood is not None:
                record.mood = mood

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_user_date(self, *, user_id: int, record_date: date) -> UserBodyStatusRecord | None:
        stmt = (
            select(UserBodyStatusRecord)
            .where(
                UserBodyStatusRecord.user_id == user_id,
                UserBodyStatusRecord.record_date == record_date,
            )
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_between_dates(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[UserBodyStatusRecord]:
        stmt = (
            select(UserBodyStatusRecord)
            .where(
                UserBodyStatusRecord.user_id == user_id,
                UserBodyStatusRecord.record_date >= start_date,
                UserBodyStatusRecord.record_date <= end_date,
            )
            .order_by(UserBodyStatusRecord.record_date.asc())
        )
        return list(self.session.scalars(stmt))

    @staticmethod
    def _append_raw_text(existing_text: str | None, new_text: str) -> str:
        normalized_existing = (existing_text or "").strip()
        normalized_new = BodyStatusRecordRepository._format_raw_text_entry(new_text)
        if not normalized_existing:
            return normalized_new
        if not normalized_new:
            return normalized_existing

        return f"{normalized_existing}\n{normalized_new}"

    @staticmethod
    def _format_raw_text_entry(raw_text: str) -> str:
        normalized_text = raw_text.strip()
        if not normalized_text:
            return ""
        current_time = datetime.now().strftime("%H:%M")
        return f"[{current_time}] {normalized_text}"
