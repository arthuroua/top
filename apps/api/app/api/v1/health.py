from fastapi import APIRouter

from app.db import get_current_revision

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | None]:
    return {
        "status": "ok",
        "migration_revision": get_current_revision(),
    }
