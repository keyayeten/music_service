from dotenv import load_dotenv
from fastapi import FastAPI

from backend.api.system.router import router as system_router
from backend.api.v1.router import router as api_v1_router
from backend.config.settings import get_settings

load_dotenv()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.include_router(system_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
