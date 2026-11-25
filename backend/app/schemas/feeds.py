"""Modèles Pydantic des routes de veille (actualités et recherche)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FeedItemOut(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    published_at: datetime | None = None
    source_id: str
    source_name: str
    tag: str | None = None


class SourceStatusOut(BaseModel):
    id: str
    name: str
    status: Literal["ok", "stale", "error"]
    via: Literal["rss", "pubmed"] | None = None
    fetched_at: datetime | None = None
    count: int


class FeedResponse(BaseModel):
    items: list[FeedItemOut]
    sources: list[SourceStatusOut]
    generated_at: datetime
