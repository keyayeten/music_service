from fastapi import APIRouter, Depends

from backend.api.deps import get_app_settings
from backend.config.settings import Settings

router = APIRouter(tags=["system"])


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "music_service is running"}


@router.get("/health")
def health(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "database_url": settings.database_url,
        "redis_url": settings.redis_url,
    }
