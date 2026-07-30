from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from sqlalchemy.orm import Session

from fitmind_agent.db.session import get_db_session
from fitmind_agent.schemas.workout_history import MuscleGroup
from fitmind_agent.schemas.workout_history import WorkoutHistoryResponse
from fitmind_agent.services.workout_history_service import WorkoutHistoryService
from fitmind_agent.services.workout_history_service import WorkoutHistoryValidationError

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/history", response_model=WorkoutHistoryResponse)
def get_workout_history(
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    muscle_group: MuscleGroup | None = None,
    exercise_keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db_session),
) -> WorkoutHistoryResponse:
    service = WorkoutHistoryService()
    try:
        filters = service.build_filters(
            start_date=start_date,
            end_date=end_date,
            muscle_group=muscle_group,
            exercise_keyword=exercise_keyword,
        )
        return service.query_history(
            user_id=user_id,
            filters=filters,
            page=page,
            page_size=page_size,
            db=db,
        )
    except WorkoutHistoryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
