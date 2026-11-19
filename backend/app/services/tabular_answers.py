"""Formatting and validation of tabular analysis results."""
from __future__ import annotations

import re

import httpx

from app.core.errors import ConfigurationError, OutOfRange, QueryError
from app.domain import prompts, router
from app.domain.formatting import (
    column_label,
    format_history,
    format_result,
    fmt_value,
    grounded,
    numbers_in,
)
from app.domain.models import AnswerResult
from app.infrastructure.llm import ollama
from app.services.answer_language import _ensure_language
from app.services.answer_messages import (
    ANALYSIS_DOWN,
    ANALYSIS_ERROR,
    LLM_DOWN,
    NO_RESULT,
    NO_VALUE,
    OUT_OF_RANGE,
    RESULTS_CALCULATED,
    SINGLE_VALUE,
)


def _compose(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[tuple],
    notes: list[str],
    history,
    language: str = "en",
) -> str:
    body = format_result(columns, rows, language) if rows else NO_RESULT[language]
    note_text = "\n".join(notes) or {
        "en": "None.",
        "fr": "Aucune.",
        "mg": "Tsy misy.",
    }[language]
    candidate = ollama.complete(
        prompts.render(
            "summary",
            history=format_history(history or []),
            question=question,
            sql=sql or "(aucun)",
            columns=", ".join(column_label(column, language) for column in columns) or "(none)",
            result=body,
            notes=note_text,
            language=router.language_name(language),
        ),
        300,
    )
    candidate = _ensure_language(candidate, language, "SQL")
    prose = "\n".join(
        line for line in candidate.splitlines()
        if not line.lstrip().startswith("|")
        and not re.fullmatch(r"[\s|:+-]+", line)
    )
    scalar_numbers = numbers_in(body) if len(rows) == len(columns) == 1 else set()
    valid = bool(
        router.has_useful_content(prose)
        and grounded(prose, body, note_text)
        and scalar_numbers <= numbers_in(prose)
    )
    scalar = len(rows) == len(columns) == 1
    if valid:
        summary = prose.strip()
    elif scalar:
        value = rows[0][0]
        summary = NO_VALUE[language] if value is None else SINGLE_VALUE[language].format(
            value=fmt_value(value),
        )
    else:
        summary = RESULTS_CALCULATED[language] if rows else note_text

    parts = [summary]
    if rows and not scalar and (len(rows) > 1 or len(columns) > 1 or not valid):
        parts.append(body)
    if notes and rows:
        note_prefix = {"en": "Note:", "fr": "À noter :", "mg": "Marihina:"}[language]
        parts.append("\n".join(f"{note_prefix} {note}" for note in notes))
    return "\n\n".join(parts)


def _tabular(mode: str, question: str, history, runner, language: str) -> AnswerResult:
    try:
        run = runner()
    except ConfigurationError as exc:
        return AnswerResult(
            ANALYSIS_DOWN[language],
            "SQL",
            raw_result=str(exc),
            audit_stage="configuration",
        )
    except OutOfRange as exc:
        try:
            text = _compose(question, "", [], [], [str(exc)], history, language)
        except httpx.HTTPError:
            text = OUT_OF_RANGE[language]
        return AnswerResult(text, "SQL", audit_stage="plage de dates")
    except QueryError as exc:
        return AnswerResult(
            ANALYSIS_ERROR[language],
            "SQL",
            exc.sql,
            exc.details,
            audit_stage=exc.stage,
        )
    try:
        notes = [_ensure_language(note, language, "SQL note") for note in run.notes]
        text = _compose(question, run.sql, run.columns, run.rows, notes, history, language)
    except httpx.HTTPError as exc:
        return AnswerResult(
            LLM_DOWN[router.detect_lang(question)],
            "SQL",
            run.sql,
            str(exc)[:300],
            audit_stage="llm",
        )
    return AnswerResult(
        text,
        mode,
        run.sql,
        format_result(run.columns, run.rows, language) if run.rows else NO_RESULT[language],
        notes=tuple(notes),
        data={
            "columns": [column_label(column, language) for column in run.columns],
            "rows": [[fmt_value(value) for value in row] for row in run.rows],
        },
    )
