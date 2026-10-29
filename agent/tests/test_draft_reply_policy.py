from types import SimpleNamespace
from unittest.mock import Mock
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from fitmind_agent.db.models import Base, User, UserWorkoutRecord
from fitmind_agent.schemas.workout import WorkoutRecordDraftPayload, WorkoutExerciseDraft

from fitmind_agent.services.draft_reply_policy import classify_draft_reply
from fitmind_agent.services.workout_record_service import WorkoutRecordService
from fitmind_agent.services.workout_plan_service import WorkoutPlanService
from fitmind_agent.services.body_status_record_service import BodyStatusRecordService
from fitmind_agent.services.nutrition_record_service import NutritionRecordService


@pytest.mark.parametrize("message", ["确认保存", "好的", "可以", "没问题！", "确认保存。"])
def test_explicit_confirmation(message):
    assert classify_draft_reply(message) == "confirm"


@pytest.mark.parametrize("message", [
    "可以把重量改成55kg吗", "好的，改成55kg", "确认前先修改次数", "保存前补充一组",
    "不是60kg，是55kg", "保存55kg", "别保存", "不要确认", "保存后能修改吗？",
])
def test_other_messages_never_confirm(message):
    assert classify_draft_reply(message) != "confirm"


@pytest.mark.parametrize("message", ["取消保存", "不保存", "先不保存", "放弃"])
def test_explicit_cancellation(message):
    assert classify_draft_reply(message) == "cancel"


class ExtractionReached(Exception):
    pass


@pytest.mark.parametrize("service_class,extractor", [
    (WorkoutRecordService, "_extract_draft"),
    (WorkoutPlanService, "_extract_draft"),
    (BodyStatusRecordService, "_extract_payload"),
    (NutritionRecordService, "_extract_payload"),
])
def test_polite_correction_reaches_extraction_without_saving(service_class, extractor):
    service = object.__new__(service_class)
    service.draft_repo = Mock()
    service._persist_draft = Mock()
    service._persist_payload = Mock()
    setattr(service, extractor, Mock(side_effect=ExtractionReached))
    draft = SimpleNamespace(id=1, user_id=1, raw_text="原始记录", draft_payload={})

    with pytest.raises(ExtractionReached):
        service._handle_pending_draft(
            pending_draft=draft, user_query="可以把重量改成55kg吗",
        )

    service._persist_draft.assert_not_called()
    service._persist_payload.assert_not_called()
    service.draft_repo.update.assert_not_called()


def test_correction_requires_new_confirmation_before_persisting():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="draft@example.com", username="draft", password_hash="unused")
        db.add(user)
        db.commit()
        service = WorkoutRecordService(db, llm_service=Mock())
        payload = WorkoutRecordDraftPayload(
            record_date=date(2026, 10, 29),
            exercises=[WorkoutExerciseDraft(exercise_name="卧推", weight_text="60kg")],
        )
        draft = service.draft_repo.create({
            "user_id": user.id, "status": "pending", "raw_text": "卧推60kg",
            "draft_payload": payload.model_dump(mode="json"),
        })
        corrected = payload.model_copy(deep=True)
        corrected.exercises[0].weight_text = "55kg"
        service._extract_draft = Mock(return_value=corrected)

        result = service._handle_pending_draft(
            pending_draft=draft, user_query="可以把重量改成55kg吗",
        )
        assert result.action == "draft_updated"
        assert draft.status == "pending"
        assert db.scalar(select(UserWorkoutRecord)) is None

        result = service._handle_pending_draft(pending_draft=draft, user_query="确认保存")
        assert result.action == "confirmed"
        assert draft.status == "confirmed"
        record = db.scalar(select(UserWorkoutRecord))
        assert record.items[0].weight_text == "55kg"
