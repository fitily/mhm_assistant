"""Reconnaissance des périodes (« mars 2026 », « mois dernier », « en 2025 »)."""
from __future__ import annotations

import datetime as dt
import re

from app.domain.models import Period

MONTH_ALIASES = {
    "janvier": ("janvier", "janv", "javier", "january", "jan"),
    "février": ("février", "fevrier", "févr", "fevr", "february", "feb"),
    "mars": ("mars", "march"),
    "avril": ("avril", "april", "apr"),
    "mai": ("mai", "may"),
    "juin": ("juin", "june"),
    "juillet": ("juillet", "juil", "july", "jul"),
    "août": ("août", "aout", "august", "aug"),
    "septembre": ("septembre", "sept", "september", "sep"),
    "octobre": ("octobre", "october", "oct"),
    "novembre": ("novembre", "november", "nov"),
    "décembre": ("décembre", "decembre", "déc", "dec", "december"),
}
MONTH_LOOKUP = {
    alias.casefold(): n
    for n, aliases in enumerate(MONTH_ALIASES.values(), start=1)
    for alias in aliases
}
_PATTERN = "|".join(re.escape(a) for al in MONTH_ALIASES.values() for a in sorted(al, key=len, reverse=True))
MONTH_YEAR_RE = re.compile(rf"\b({_PATTERN})\.?\s+((?:19|20)\d{{2}})\b", re.I)
YEAR_RE = re.compile(r"\b(?:en|in|pour|durant|année|annee|year)\s+((?:19|20)\d{2})\b", re.I)
LAST_MONTH_RE = re.compile(r"\b(mois dernier|mois passé|mois passe|last month)\b", re.I)
THIS_MONTH_RE = re.compile(r"\b(ce mois|mois en cours|this month)\b", re.I)


def normalize_question(question: str) -> str:
    """Corrige les fautes courantes sur les mois (javier, fevrier, dec...)."""
    out = question
    for canonical, aliases in MONTH_ALIASES.items():
        for alias in aliases:
            if alias != canonical:
                out = re.sub(rf"\b{re.escape(alias)}\b", canonical, out, flags=re.I)
    return out


def next_month(d: dt.date) -> dt.date:
    return dt.date(d.year + 1, 1, 1) if d.month == 12 else dt.date(d.year, d.month + 1, 1)


def parse_period(question: str, today: dt.date) -> Period | None:
    normalized = normalize_question(question)
    m = MONTH_YEAR_RE.search(normalized)
    if m:
        start = dt.date(int(m.group(2)), MONTH_LOOKUP[m.group(1).casefold()], 1)
        return Period(start, next_month(start), f"{m.group(1)} {m.group(2)}")
    if LAST_MONTH_RE.search(question):
        first = today.replace(day=1)
        return Period((first - dt.timedelta(days=1)).replace(day=1), first, "mois dernier")
    if THIS_MONTH_RE.search(question):
        start = today.replace(day=1)
        return Period(start, next_month(start), "ce mois")
    y = YEAR_RE.search(question)
    if y:
        year = int(y.group(1))
        return Period(dt.date(year, 1, 1), dt.date(year + 1, 1, 1), str(year))
    return None
