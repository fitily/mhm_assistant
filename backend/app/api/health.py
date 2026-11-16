"""GET /health (vivant ?) et GET /health/ready (base, vecteurs et Ollama joignables ?)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.infrastructure.db import analytics, vectors
from app.infrastructure.llm import ollama

router = APIRouter(tags=["health"])


def _db_ok(engine_factory) -> bool:
    try:
        with engine_factory().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - un test de santé ne doit jamais planter
        return False


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready():
    checks = {"analytics_db": _db_ok(analytics.engine), "vector_db": _db_ok(vectors.engine),
              "ollama": ollama.is_up()}
    return JSONResponse(checks, status_code=200 if all(checks.values()) else 503)
