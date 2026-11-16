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
    "total_patients": {"en": "Patients", "fr": "Patients", "mg": "Marary"},
    "patients": {"en": "Patients", "fr": "Patients", "mg": "Marary"},
    "total_admissions": {"en": "Admissions", "fr": "Admissions", "mg": "Fampidirana"},
    "admissions": {"en": "Admissions", "fr": "Admissions", "mg": "Fampidirana"},
    "total_deaths": {"en": "Deaths", "fr": "Décès", "mg": "Maty"},
    "total_consultations": {"en": "Consultations", "fr": "Consultations", "mg": "Fizahana"},
    "total_diagnoses": {"en": "Diagnoses", "fr": "Diagnostics", "mg": "Diagnostika"},
    "total_visits": {"en": "Visits", "fr": "Visites", "mg": "Fitsidihana"},
    "patient_count": {"en": "Patients", "fr": "Patients", "mg": "Marary"},
    "visit_count": {"en": "Admissions", "fr": "Admissions", "mg": "Fampidirana"},
    "count": {"en": "Count", "fr": "Nombre", "mg": "Isa"},
    "n": {"en": "Count", "fr": "Nombre", "mg": "Isa"},
    "age_group": {"en": "Age group", "fr": "Tranche d'âge", "mg": "Sokajin-taona"},
    "gender": {"en": "Gender", "fr": "Sexe", "mg": "Lahy/Vavy"},
    "district": {"en": "District", "fr": "District", "mg": "Distrika"},
    "commune": {"en": "Commune", "fr": "Commune", "mg": "Kaominina"},
    "month": {"en": "Month", "fr": "Mois", "mg": "Volana"},
    "visit_date": {"en": "Visit date", "fr": "Date de visite", "mg": "Datin'ny fitsidihana"},
    "diagnosis_label": {"en": "Diagnosis", "fr": "Diagnostic", "mg": "Diagnostika"},
}


def column_label(name: str, language: str = "en") -> str:
    labels = _COLUMN_LABELS.get(name.casefold())
    return labels.get(language, labels["en"]) if labels else name.replace("_", " ").capitalize()


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


def format_result(columns: list[str], rows: list[tuple], language: str = "en") -> str:
    labels = [column_label(c, language) for c in columns]
    if len(rows) == 1 and len(columns) == 1:
        label = labels[0].strip() or {"en": "Result", "fr": "Résultat", "mg": "Valiny"}[language]
        separator = " : " if language == "fr" else ": "
        return f"{label}{separator}{fmt_value(rows[0][0])}"
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