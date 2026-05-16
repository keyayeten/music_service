from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_v1() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}
