from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fitmind_agent.db.models import Base
from fitmind_agent.db.models import User
from fitmind_agent.repositories.nutrition import NutritionRecordRepository


def test_nutrition_daily_record_accumulates_totals_and_appends_raw_text() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="test@example.com", username="tester", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        repo = NutritionRecordRepository(session)
        record_date = date(2026, 6, 15)

        first = repo.upsert_daily_record(
            user_id=user.id,
            record_date=record_date,
            raw_text="早餐鸡蛋牛奶",
            calories_estimate=Decimal("500"),
            protein_g_estimate=Decimal("35"),
            carbs_g_estimate=Decimal("20"),
            fat_g_estimate=Decimal("18"),
        )
        second = repo.upsert_daily_record(
            user_id=user.id,
            record_date=record_date,
            raw_text="牛肉200g",
            calories_estimate=Decimal("400"),
            protein_g_estimate=Decimal("52"),
            carbs_g_estimate=Decimal("0"),
            fat_g_estimate=Decimal("24"),
        )

        assert first.id == second.id
        assert second.calories_estimate == Decimal("900.00")
        assert second.protein_g_estimate == Decimal("87.00")
        assert second.carbs_g_estimate == Decimal("20.00")
        assert second.fat_g_estimate == Decimal("42.00")
        assert "早餐鸡蛋牛奶" in second.raw_text
        assert "牛肉200g" in second.raw_text
        assert "今日累计蛋白约87g" in second.raw_text
        assert "热量约900kcal" in second.raw_text
        assert second.raw_text.count("\n") == 1
