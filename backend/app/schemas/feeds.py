"""Response models for the medical news feed."""
from __future__ import annotations

from pydantic import BaseModel


class NewsArticleOut(BaseModel):
    id: str
    title: str
    summary: str = ""
    source: str
    url: str
    published_at: str | None = None
    category: str
    image: str | None = None


class NewsSourceOut(BaseModel):
    key: str
    label: str
    url: str
    connected: bool


class NewsFeedOut(BaseModel):
    items: list[NewsArticleOut]
    updated_at: str
    connected: bool
    sources: list[NewsSourceOut]
    window_days: int = 7          # période affichée : les N derniers jours
    since: str | None = None      # début de cette période (ISO, UTC)
    outside_window: int = 0       # articles correspondant aux filtres mais hors période (non affichés)
