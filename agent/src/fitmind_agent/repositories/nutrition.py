from __future__ import annotations

from datetime import date
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import UserBodyStatusRecord
from fitmind_agent.db.models import UserNutritionRecord


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
        data = {
            "raw_text": self._format_raw_text_entry(raw_text),
            "calories_estimate": calories_estimate,
            "protein_g_estimate": protein_g_estimate,
            "carbs_g_estimate": carbs_g_estimate,
            "fat_g_estimate": fat_g_estimate,
        }

        if record is None:
            record = UserNutritionRecord(user_id=user_id, record_date=record_date, **data)
        else:
            record.raw_text = self._append_raw_text(record.raw_text, raw_text)
            if calories_estimate is not None:
                record.calories_estimate = calories_estimate
            if protein_g_estimate is not None:
                record.protein_g_estimate = protein_g_estimate
            if carbs_g_estimate is not None:
                record.carbs_g_estimate = carbs_g_estimate
            if fat_g_estimate is not None:
                record.fat_g_estimate = fat_g_estimate

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

    @staticmethod
    def _append_raw_text(existing_text: str | None, new_text: str) -> str:
        normalized_existing = (existing_text or "").strip()
        normalized_new = NutritionRecordRepository._format_raw_text_entry(new_text)
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
