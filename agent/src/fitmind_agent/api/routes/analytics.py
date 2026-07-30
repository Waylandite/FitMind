from datetime import date

from fastapi import APIRouter
from fastapi import HTTPException

from fitmind_agent.schemas.weekly_analytics import WeeklyAnalyticsResponse
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsQueryError
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsService
from fitmind_agent.services.weekly_analytics_service import WeeklyAnalyticsValidationError


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/weekly", response_model=WeeklyAnalyticsResponse)
def get_weekly_analytics(
    user_id: int,
    anchor_date: date | None = None,
) -> WeeklyAnalyticsResponse:
    try:
        return WeeklyAnalyticsService().analyze(
            user_id=user_id,
            anchor_date=anchor_date,
        )
    except WeeklyAnalyticsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WeeklyAnalyticsQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
