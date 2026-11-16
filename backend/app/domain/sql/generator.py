"""Génération du SQL par le LLM : choix des vues, prompt, nettoyage de la réponse."""
from __future__ import annotations

import datetime as dt
import json
import re

from app.core.config import get_settings
from app.core.dictionary import dictionary
from app.domain import prompts
from app.domain.formatting import format_history
from app.domain.models import Period
from app.infrastructure.db.analytics import view_columns
from app.domain.sql.examples import prompt_examples
from app.infrastructure.llm import ollama


def select_views(question: str, views: dict) -> list[tuple[tuple[str, str], dict]]:
    """Fournit au LLM le schéma réel complet des vues autorisées."""
    return list(views.items())


def schema_prompt(selected) -> str:
    blocks = []
    for (schema, view), meta in selected:
        docs = meta.get("columns") or {}
        lines = [f"{schema}.{view} : {' '.join(str(meta.get('description', '')).split())}"]
        for name, ctype in view_columns(schema, view):
            doc = docs.get(name, "")
            lines.append(f"  - {name} ({ctype}){' : ' + doc if doc else ''}")
        blocks.append("\n".join(lines))
    definitions = dictionary().get("glossary", {})
    glossary = "\n".join(f"- {k} : {v}" for k, v in definitions.items())
    return ("\n\n".join(blocks) + "\n\nDéfinitions métier :\n"
            "Patient = fiche non supprimée. Admission = une visite. "
            "Mortalité = patient_dead. Date de référence = created_at.\n"
            + glossary)


def period_hint(period: Period | None, selected) -> str:
    if not period:
        return ""
    return (f"Période demandée : {period.label}. Filtre la colonne date appropriée de la vue "
            "choisie avec >= :start et < :end. Les paramètres start et end sont liés par le code.")


def clean_sql(generated: str) -> str:
    return re.sub(r"^\s*```(?:sql)?\s*|\s*```\s*$", "", generated, flags=re.I).strip()


def generate(question: str, history, today: dt.date, schema_txt: str, hint: str,
             correction: str) -> tuple[str, dict]:
    prompt = prompts.render(
        "sql", max_rows=get_settings().max_sql_rows, today=today, schema=schema_txt,
        question=question, period_hint=hint, correction=correction,
        examples=prompt_examples(),
        history=format_history(history or []))
    raw = ollama.complete(prompt, predict=500, temperature=0, response_format="json")
    data = json.loads(clean_sql(raw))
    if not isinstance(data, dict) or not isinstance(data.get("sql"), str):
        raise ValueError("Le modèle doit retourner un objet JSON avec sql et params.")
    params = data.get("params", {})
    if not isinstance(params, dict) or any(
            not isinstance(v, (str, int, float, bool, type(None))) for v in params.values()):
        raise ValueError("Les paramètres SQL doivent être des valeurs simples.")
    if any(not re.fullmatch(r"[A-Za-z_]\w*", str(k)) for k in params):
        raise ValueError("Nom de paramètre SQL invalide.")
    return data["sql"], params
