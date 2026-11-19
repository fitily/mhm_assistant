"""Question orchestration: validation, routing, answer generation and audit."""
from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import replace

import httpx

from app.core.audit import audit
from app.core.config import debug_trace, get_settings
from app.core.dictionary import approved_views
from app.domain import prompts, router
from app.domain.formatting import format_history
from app.domain.models import AnswerResult
from app.domain.periods import normalize_question, parse_period
from app.domain.retrieval.documents import get_doc_context
from app.domain.sql.executor import run_sql
from app.infrastructure.llm import ollama
from app.services.answer_language import _ensure_language, _is_language_prefix
from app.services.answer_messages import (
    ANALYSIS_DOWN,
    ANALYSIS_ERROR,
    DOCS_DOWN,
    LLM_DOWN,
    LLM_TIMEOUT,
    NO_DOC,
    NO_RESULT,
    NO_VALUE,
    OUT_OF_RANGE,
    RESULTS_CALCULATED,
    SINGLE_VALUE,
)
from app.services.document_answers import (
    _clean_doc_reply,
    _doc_error,
    _doc_sources,
    _guard_research_claims,
    _guard_research_percentages,
    _is_research_context,
    _knowledge_attitude_link_polarities,
    _research_guidance,
)
from app.services import document_answers
from app.services.tabular_answers import _compose, _tabular


def _docs(
    question: str,
    lang: str,
    history,
    on_docs_wait: Callable[[], None] | None = None,
    on_docs_token: Callable[[str], None] | None = None,
) -> AnswerResult:
    return document_answers._docs(
        question,
        lang,
        history,
        on_docs_wait,
        on_docs_token,
        context_loader=get_doc_context,
    )


def _general(question: str, original: str, lang: str, history) -> AnswerResult:
    """Generate a chat-only response and reject unsupported medical or numeric claims."""
    summary = router.is_summary_request(question)
    prompt_name = "conversation_summary" if summary else "general"
    prompt = prompts.render(
        prompt_name,
        question=question,
        history=format_history(history or []),
        language=router.language_name(lang),
    )
    try:
        reply = ollama.complete(prompt, 300, temperature=0.3)
        reply = _ensure_language(reply, lang, "CHAT")
    except Exception as exc:
        return AnswerResult(
            LLM_DOWN[lang],
            "CHAT",
            raw_result=str(exc)[:300],
            audit_stage="llm",
        )
    guarded = router.guard_general((reply or "").strip(), original, history)
    if guarded != (reply or "").strip():
        debug_trace(
            "CHAT rejet",
            reason="garde-fou médical ou chiffre non vérifié",
            question=original,
            answer=(reply or "").strip(),
        )
    return AnswerResult(guarded, "CHAT")


def _answer(
    question: str,
    original: str,
    forced,
    history,
    decision: router.Route | None,
    on_docs_wait: Callable[[], None] | None = None,
    on_docs_token: Callable[[str], None] | None = None,
) -> AnswerResult:
    """Route a question and execute only the selected answer generator."""
    language = router.detect_lang(original)
    if forced:
        quick = router.quick_reply(question, allow_chat_replies=False)
        if quick:
            return AnswerResult(_ensure_language(quick[1], language, "réponse rapide"), "CHAT")
        mode = forced
    else:
        assert decision is not None
        if decision.response:
            return AnswerResult(
                _ensure_language(decision.response, language, "réponse rapide"),
                "CHAT",
            )
        mode = decision.name.upper()

    today = dt.datetime.now(get_settings().tz).date()
    period = parse_period(normalize_question(question), today)
    if mode == "SQL":
        return _tabular(
            "SQL",
            question,
            history,
            lambda: run_sql(question, approved_views(), history, period),
            language,
        )
    if mode == "DOCS":
        return _docs(question, language, history, on_docs_wait, on_docs_token)
    return _general(question, original, language, history)


def answer(
    question: str,
    *,
    forced: str | None = None,
    history=None,
    user: str = "inconnu",
    on_docs_wait: Callable[[], None] | None = None,
    on_docs_token: Callable[[str], None] | None = None,
) -> AnswerResult:
    question = " ".join(question.split())
    language = router.detect_lang(question)
    if not question:
        return AnswerResult("Please enter a question.", "CHAT")
    if len(question) > get_settings().max_question_chars:
        messages = {
            "en": "Please shorten your question (maximum 2,000 characters).",
            "fr": "Veuillez raccourcir la question (2 000 caractères maximum).",
            "mg": "Afohezo kokoa ny fanontanianao azafady (tsy mihoatra ny litera 2 000).",
        }
        return AnswerResult(messages[language], "CHAT")
    if forced and forced not in {"SQL", "DOCS"}:
        raise ValueError("Le mode forcé doit être SQL ou DOCS.")

    debug_trace(
        "Timeouts configurés",
        ollama_connect_seconds=10,
        ollama_read_seconds=180,
        ollama_write_seconds=10,
        ollama_pool_seconds=10,
        ollama_healthcheck_seconds=3,
        sql_statement_ms=get_settings().sql_timeout_ms,
        sql_idle_transaction_ms=30000,
    )
    decision = None
    try:
        if forced:
            standalone = router.rewrite_followup(question, history)
        else:
            decision = router.route(question, history)
            standalone = decision.question
    except httpx.TimeoutException as exc:
        result = AnswerResult(
            LLM_TIMEOUT[language],
            forced or "CHAT",
            raw_result=str(exc)[:300],
            audit_stage="llm_timeout",
        )
        audit(user, question, result.mode, result.audit_stage, None, None)
        return result

    debug_trace(
        "Routage",
        received=question,
        rewritten=standalone,
        language=router.detect_lang(question),
        mode=forced or (decision.name.upper() if decision else "CHAT"),
    )
    result = _answer(
        standalone,
        question,
        forced,
        history,
        decision,
        on_docs_wait,
        on_docs_token,
    )
    shown = question if standalone == question else f"{question} → {standalone}"
    if not router.has_useful_content(result.text):
        debug_trace(
            "Réponse rejetée",
            reason="filtre de réponse inutile",
            mode=result.mode,
            answer=result.text,
        )
        messages = {
            "fr": "Je n'ai pas pu formuler une réponse utile. Pouvez-vous préciser votre demande ?",
            "mg": "Tsy afaka namorona valiny mahasoa aho. Azafady, hazavao kokoa ny fangatahanao.",
            "en": "I couldn't produce a useful answer. Could you clarify your request?",
        }
        result = replace(result, text=messages[language])
    audit(
        user,
        shown,
        result.mode,
        result.audit_stage,
        result.sql,
        len(result.data["rows"]) if result.data else None,
    )
    return result
