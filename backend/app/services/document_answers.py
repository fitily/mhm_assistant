"""Grounded document-answer generation and research-claim safeguards."""
from __future__ import annotations

import re
import time
from collections.abc import Callable
from textwrap import wrap

import httpx

from app.core.config import debug_trace
from app.core.errors import ConfigurationError
from app.domain import prompts, router
from app.domain.formatting import format_history
from app.domain.models import AnswerResult
from app.domain.retrieval.documents import get_doc_context
from app.infrastructure.llm import ollama
from app.services.answer_messages import DOCS_DOWN, LLM_DOWN, LLM_TIMEOUT, NO_DOC
from app.services.answer_language import _is_language_prefix
from app.services.document_guards import (
    _guard_research_claims,
    _guard_research_percentages,
    _is_research_context,
    _knowledge_attitude_link_polarities,
    _research_guidance,
)


def _doc_sources(text: str, sources, language: str) -> str:
    separator = " ; " if language == "fr" else "; "
    citations = separator.join(label for _, label in sources)
    heading = {"en": "Sources:", "fr": "Sources :", "mg": "Loharano:"}[language]
    return f"{text}\n\n{heading} {citations}" if citations else text


def _doc_error(
    message: str,
    context: str,
    error: str | None = None,
    stage: str = "llm",
) -> AnswerResult:
    excerpts = re.findall(r"(?m)^\[([^\]\n]+)\]\n(.*?)(?=^---\s*$|\Z)", context, re.S)
    lines = [message]
    for label, content in excerpts[:3]:
        content = re.sub(r"(?m)^\[RAG section=[^\]]+\]\s*\n", "", content)
        excerpt_lines = [
            line
            for raw_line in content.strip().splitlines()
            for line in wrap(
                raw_line,
                width=100,
                break_long_words=False,
                break_on_hyphens=False,
            )
        ][:3]
        if excerpt_lines:
            lines.append(f"{label}\n" + "\n".join(excerpt_lines))
    return AnswerResult("\n\n".join(lines), "DOCS", raw_result=error, audit_stage=stage)


def _docs(
    question: str,
    lang: str,
    history,
    on_docs_wait: Callable[[], None] | None = None,
    on_docs_token: Callable[[str], None] | None = None,
    context_loader: Callable = get_doc_context,
) -> AnswerResult:
    try:
        context, sources = context_loader(question, history, lang)
    except httpx.TimeoutException as exc:
        return _doc_error(LLM_TIMEOUT[lang], "", str(exc)[:300], "llm_timeout")
    except ConfigurationError:
        message = {
            "en": "Document search is not available at the moment.",
            "fr": "La recherche documentaire n'est pas disponible pour le moment.",
            "mg": "Tsy misy amin'izao fotoana izao ny fikarohana antontan-taratasy.",
        }[lang]
        return AnswerResult(message, "DOCS", audit_stage="configuration")
    except Exception as exc:
        return AnswerResult(
            DOCS_DOWN[lang],
            "DOCS",
            raw_result=str(exc)[:300],
            audit_stage="documents",
        )
    if not context:
        debug_trace("DOCS rejet", reason="aucun passage au-dessus du seuil")
        return AnswerResult(NO_DOC[lang], "DOCS")
    prompt = prompts.render(
        "docs",
        history=format_history(history or []),
        context=context,
        question=question,
        language=router.language_name(lang),
        research_guidance=_research_guidance(context, lang),
    )
    research_context = _is_research_context(context)
    try:
        if on_docs_wait:
            on_docs_wait()
        buffered_sentence = ""
        pending_language_tokens: list[str] = []
        language_stream_started = False

        def emit_language_safe(piece: str) -> None:
            nonlocal language_stream_started
            if not on_docs_token:
                return
            if language_stream_started:
                on_docs_token(piece)
                return
            pending_language_tokens.append(piece)
            if _is_language_prefix("".join(pending_language_tokens), lang):
                on_docs_token("".join(pending_language_tokens))
                pending_language_tokens.clear()
                language_stream_started = True

        def emit_guarded(piece: str) -> None:
            nonlocal buffered_sentence
            if not on_docs_token:
                return
            buffered_sentence += piece
            completed = re.split(r"(?<=[.!?])\s+", buffered_sentence)
            buffered_sentence = completed.pop()
            for sentence in completed:
                guarded = _guard_research_claims(sentence, context, lang)
                emit_language_safe(_guard_research_percentages(guarded, context, lang))

        reply = ollama.stream(
            prompt,
            predict=200,
            emit=(
                emit_guarded
                if on_docs_token and research_context
                else emit_language_safe if on_docs_token else None
            ),
            stage="génération DOCS",
            num_ctx=4096,
        )
        if buffered_sentence and on_docs_token and research_context:
            guarded = _guard_research_claims(buffered_sentence, context, lang)
            emit_language_safe(_guard_research_percentages(guarded, context, lang))
        clean_reply = _clean_doc_reply(reply)
        clean_reply = _guard_research_claims(clean_reply, context, lang)
        clean_reply = _guard_research_percentages(clean_reply, context, lang)
        verification_started = time.perf_counter()
        detected_lang = router.detect_lang(clean_reply)
        debug_trace(
            "DOCS étape",
            stage="vérification de langue",
            duration_ms=round((time.perf_counter() - verification_started) * 1000, 2),
            prompt_tokens=ollama.estimate_tokens(clean_reply),
            result_tokens=ollama.estimate_tokens(detected_lang),
            token_count_source="estimated",
        )
        if clean_reply and detected_lang != lang:
            debug_trace(
                "DOCS langue",
                reason="traduction nécessaire",
                requested=lang,
                detected=detected_lang,
            )
            translation = prompts.render(
                "answer_translation",
                language=router.language_name(lang),
                answer=clean_reply,
            )
            clean_reply = _clean_doc_reply(ollama.complete(
                translation,
                200,
                temperature=0,
                stage="traduction de la réponse",
                num_ctx=4096,
            ))
            verification_started = time.perf_counter()
            detected_lang = router.detect_lang(clean_reply)
            debug_trace(
                "DOCS étape",
                stage="vérification de langue",
                duration_ms=round((time.perf_counter() - verification_started) * 1000, 2),
                prompt_tokens=ollama.estimate_tokens(clean_reply),
                result_tokens=ollama.estimate_tokens(detected_lang),
                token_count_source="estimated",
            )
    except httpx.TimeoutException as exc:
        debug_trace("DOCS rejet", reason="délai de génération dépassé", error=str(exc))
        return _doc_error(LLM_TIMEOUT[lang], context, str(exc)[:300], "llm_timeout")
    except Exception as exc:
        debug_trace("DOCS rejet", reason="échec de génération", error=str(exc))
        return _doc_error(LLM_DOWN[lang], context, str(exc)[:300], "llm")
    if detected_lang != lang:
        debug_trace(
            "DOCS rejet",
            reason="langue de réponse non conforme",
            requested=lang,
            answer=clean_reply,
        )
        return _doc_error(LLM_DOWN[lang], context, stage="response_language")
    if not router.has_useful_content(clean_reply):
        debug_trace("DOCS rejet", reason="filtre de réponse inutile", answer=clean_reply)
        return AnswerResult(_doc_sources(NO_DOC[lang], sources, lang), "DOCS", sources=tuple(sources))
    if on_docs_token and not language_stream_started:
        on_docs_token(clean_reply)
    return AnswerResult(_doc_sources(clean_reply, sources, lang), "DOCS", sources=tuple(sources))


def _clean_doc_reply(reply: str) -> str:
    without_sources = re.sub(r"(?im)^\s*(?:sources?|références?)\s*:\s*.*$", "", reply)
    return re.sub(r"\s*\[[^\]\n]*\]", "", without_sources).strip()
