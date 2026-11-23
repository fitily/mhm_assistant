"""Modèles Pydantic de l'API (entrée / sortie)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    mode: Literal["SQL", "DOCS"] | None = None  # force la source ; sinon routage automatique


class ClearRequest(BaseModel):
    session_id: str | None = None


class Source(BaseModel):
    score: float
    label: str


class ChatResponse(BaseModel):
    text: str
    sender: str
    mode: str
    sql: str | None = None
    notes: list[str] = []
    sources: list[Source] = []
    data: dict | None = None  # {"columns": [...], "rows": [[...]]} pour tableaux / graphiques
    action: dict | None = None  # ordre pour l'interface : {"type": "open_dashboard", "dashboard": "<clé>", ...}
