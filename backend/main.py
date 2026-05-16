import os

from dotenv import load_dotenv
from fastapi import FastAPI


load_dotenv()

app = FastAPI(title="music_service")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "music_service is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "database_url": os.getenv("DATABASE_URL", ""),
        "redis_url": os.getenv("REDIS_URL", ""),
    }
