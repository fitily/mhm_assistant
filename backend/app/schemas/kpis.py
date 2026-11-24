"""Modèle de sortie de GET /v1/kpis."""
from __future__ import annotations

from pydantic import BaseModel


class KpiOut(BaseModel):
    key: str
    label: str
    value: int | None = None        # None si l'indicateur est indisponible
    hint: str = ""
    delta_percent: float | None = None
    error: bool = False
