"""Mise en forme des résultats, historique de conversation et contrôle des chiffres."""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

from app.core.config import get_settings

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
# Séparateur de milliers : espace, espace insécable (\u00a0), espace fine (\u202f) ou virgule.
_THOUSANDS = re.compile(r"(?<=\d)[\u00a0\u202f ,](?=\d{3}\b)")
_COLUMN_LABELS = {
    "total_patients": "Patients",
    "patients": "Patients",
    "total_admissions": "Admissions",
    "admissions": "Admissions",
    "total_deaths": "Décès",
    "total_consultations": "Consultations",
    "total_diagnoses": "Diagnostics",
    "total_visits": "Visites",
    "patient_count": "Patients",
    "visit_count": "Admissions",
    "count": "Nombre",
    "n": "Nombre",
    "age_group": "Tranche d'âge",
    "gender": "Sexe",
    "district": "District",
    "commune": "Commune",
    "month": "Mois",
    "visit_date": "Date de visite",
    "diagnosis_label": "Diagnostic",
}


def column_label(name: str) -> str:
    return _COLUMN_LABELS.get(name.casefold(), name.replace("_", " ").capitalize())


def fmt_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        value = int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}".replace(",", "\u202f")
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    return str(value)


def format_result(columns: list[str], rows: list[tuple]) -> str:
    labels = [column_label(c) for c in columns]
    if len(rows) == 1 and len(columns) == 1:
        label = labels[0].strip() or "Résultat"
        return f"{label} : {fmt_value(rows[0][0])}"
    table = [[fmt_value(v)[:40] for v in row] for row in rows]
    widths = [max([len(c)] + [len(r[i]) for r in table]) for i, c in enumerate(labels)]
    lines = [" | ".join(c.ljust(w) for c, w in zip(labels, widths)),
             "-+-".join("-" * w for w in widths)]
    lines += [" | ".join(v.ljust(w) for v, w in zip(r, widths)) for r in table]
    return "\n".join(lines)[: get_settings().max_result_chars]


def numbers_in(value: str) -> set[str]:
    cleaned = _THOUSANDS.sub("", value)
    return set(_NUMBER.findall(cleaned))


def grounded(summary: str, *sources: str) -> bool:
    """Tous les nombres du résumé doivent figurer dans le résultat SQL ou la question."""
    allowed = set().union(*(numbers_in(s) for s in sources))
    return numbers_in(summary) <= allowed


def format_history(history: list[tuple[str, str]]) -> str:
    """Formate les dix derniers échanges."""
    if not history:
        return "(aucune)"
    lines = []
    for q, a in history[-10:]:
        question = " ".join(q.split())[:280]
        answer = " ".join(a.split())
        short = answer[:220].rsplit(" ", 1)[0] + "..." if len(answer) > 220 else answer
        lines.append(f"User: {question}\nAssistant: {short}")
    return "\n".join(lines)