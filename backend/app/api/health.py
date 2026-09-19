from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import database_is_ready

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", response_model=None)
def ready() -> dict[str, str] | JSONResponse:
    if not database_is_ready():
        return JSONResponse(
            status_code=503,
            content={
                "code": "database_unavailable",
                "message": "数据库暂不可用",
            },
        )
    return {"status": "ready", "database": "up"}
