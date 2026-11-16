"""Objets échangés entre les modules (sans logique)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnswerResult:
    text: str
    mode: str
    sql: str | None = None
    raw_result: str | None = None
    sources: tuple[tuple[float, str], ...] = ()
    audit_stage: str | None = None
    notes: tuple[str, ...] = ()
    data: dict | None = None  # {"columns": [...], "rows": [...]} pour l'interface Vue
    streamed: bool = False


@dataclass
class SQLRun:
    sql: str
    columns: list[str]
    rows: list[tuple]
    truncated: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Period:
    start: dt.date
    end: dt.date  # exclu
    label: str
