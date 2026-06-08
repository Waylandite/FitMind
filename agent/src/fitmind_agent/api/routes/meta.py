from fastapi import APIRouter

from fitmind_agent.core.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/meta")
def get_meta() -> dict[str, str]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "api_prefix": settings.api_prefix,
    }
