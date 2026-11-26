"""GET /v1/news : actualités publiques et recherches, réservées au rôle médecin."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import require_role
from app.core.security import ROLE_DOCTOR, Principal
from app.schemas.feeds import NewsFeedOut
from app.services import feed_service

log = logging.getLogger("mhm.feeds.api")
router = APIRouter(prefix="/v1", tags=["news"])


@router.get("/news", response_model=NewsFeedOut)
async def news(
    response: Response,
    category: Literal["all", "breaking", "research", "update"] = Query("all"),
    q: str = Query("", max_length=200),
    _: Principal = Depends(require_role(ROLE_DOCTOR)),
) -> NewsFeedOut:
    try:
        payload = await feed_service.get_news()
    except feed_service.FeedsUnavailableError:
        log.warning("All configured medical news sources are unavailable.")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Medical news are temporarily unavailable. Please try again.",
        ) from None
    response.headers["Cache-Control"] = "private, no-store"
    return NewsFeedOut(**feed_service.filter_news(payload, category=category, query=q))
