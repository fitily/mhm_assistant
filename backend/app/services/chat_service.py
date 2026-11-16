"""Orchestration : une question entre, une réponse sort (sécurité → outil → audit)."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from collections.abc import Callable
from decimal import Decimal
from textwrap import wrap
import time

import httpx

from app.core.audit import audit
from app.core.config import debug_trace, get_settings
from app.core.dictionary import approved_views
from app.core.errors import ConfigurationError, OutOfRange, QueryError
from app.domain import prompts, router
from app.domain.formatting import (column_label, format_history, format_result, fmt_value,
                                   grounded, numbers_in)
from app.domain.models import AnswerResult
from app.domain.periods import normalize_question, parse_period
from app.domain.retrieval.documents import get_doc_context
from app.domain.sql.executor import run_sql
from app.infrastructure.llm import ollama

NO_DOC = {
    "fr": "Je ne trouve pas cette information dans les documents disponibles.",
    "en": "I cannot find this information in the available documents.",
    "mg": "Tsy hitako ao amin'ireo antontan-taratasy misy izany.",
}
DOCS_DOWN = {
    "fr": "La base documentaire n'est pas disponible pour le moment.",
    "en": "The document base is not available at the moment.",
    "mg": "Tsy misy amin'izao fotoana izao ny tahirin-kevitra.",
}
ANALYSIS_DOWN = {
    "fr": "L'analyse n'est pas disponible pour le moment.",
    "en": "The analysis is not available at the moment.",
    "mg": "Tsy misy amin'izao fotoana izao ny fanadihadiana.",
}
OUT_OF_RANGE = {
    "fr": "La période demandée est en dehors de la plage de données disponible.",
    "en": "The requested period is outside the available data range.",
    "mg": "Any ivelan'ny fe-potoana misy ny angona ny vanim-potoana nangatahana.",
}
NO_RESULT = {
    "fr": "Aucun résultat.",
    "en": "No results.",
    "mg": "Tsy misy valiny.",
}
_KNOWLEDGE = r"(?:(?:hiv(?:\s+transmission)?\s+)?knowledge(?:\s+(?:scores?|levels?))?|connaissances?)"
_ATTITUDES = r"(?:(?:stigmatizing\s+|stigmatisantes?\s+)?attitudes?)"
_RELATION = r"(?:correlat\w*|associat\w*|relationship|links?|related|corrélation|relations?|liens?)"
_KNOWLEDGE_ATTITUDE_LINKS = (
    re.compile(
        rf"{_RELATION}.{{0,30}}(?:between|among|entre)\s+(?:the\s+)?{_KNOWLEDGE}"
        rf".{{0,50}}(?:and|with|et)\s+(?:the\s+)?{_ATTITUDES}", re.I),
    re.compile(
        rf"(?:{_KNOWLEDGE}).{{0,40}}(?:correlat\w*|associat\w*|linked|related|li[eé]s?)"
        rf".{{0,30}}(?:to|with|à|aux|avec)\s+(?:the\s+)?{_ATTITUDES}", re.I),
    re.compile(
        rf"(?:{_ATTITUDES}).{{0,40}}(?:correlat\w*|associat\w*|linked|related|li[eé]s?)"
        rf".{{0,30}}(?:to|with|à|aux|avec)\s+(?:the\s+)?{_KNOWLEDGE}", re.I),
    re.compile(
        rf"(?:{_KNOWLEDGE}).{{0,25}}(?:and|&|et).{{0,25}}(?:{_ATTITUDES})"
        rf".{{0,25}}(?:are|were|is|was|sont|étaient)?\s*"
        rf"(?:(?:not|never|pas)\s+)?"
        rf"(?:(?:significantly|strongly|statistically|positively|negatively)\s+)?"
        rf"(?:correlat\w*|associat\w*|related|linked|li[eé]s?)", re.I),
)
LLM_DOWN = {
    "fr": "Le modèle de langage n'est pas disponible pour le moment. Réessayez dans un instant.",
    "en": "The language model is not available at the moment. Please try again shortly.",
    "mg": "Tsy misy amin'izao fotoana izao ny maodely fiteny. Andramo indray afaka kelikely.",
}
LLM_TIMEOUT = {
    "fr": "Le délai d’attente de l’IA a été dépassé.",
    "en": "The AI request timed out.",
    "mg": "Nihoatra ny fe-potoana fiandrasana ny fangatahana tamin'ny IA.",
}
ANALYSIS_ERROR = {
    "fr": "L'analyse a échoué. Aucun chiffre n'a été calculé.",
    "en": "The analysis failed. No figures were calculated.",
    "mg": "Tsy nahomby ny fanadihadiana. Tsy nisy tarehimarika voakajy.",
}
NO_VALUE = {
    "fr": "Aucune valeur numérique n'est disponible.",
    "en": "No numeric value is available.",
    "mg": "Tsy misy sanda isa azo ampiasaina.",
}
SINGLE_VALUE = {
    "fr": "Le nombre correspondant est {value}.",
    "en": "The matching number is {value}.",
    "mg": "Izao ny isa mifanaraka amin'izany: {value}.",
}
RESULTS_CALCULATED = {
    "fr": "Voici les résultats calculés.",
    "en": "Here are the calculated results.",
    "mg": "Ireto ny valin'ny kajy.",
}


def _ensure_language(text: str, language: str, stage: str) -> str:
    if not text.strip() or router.detect_lang(text) == language:
        return text
    prompt = prompts.render(
        "answer_translation", language=router.language_name(language), answer=text)
    translated = ollama.complete(
        prompt, max(200, ollama.estimate_tokens(text) + 60), temperature=0,
        stage=f"traduction {stage}").strip()
    if not translated or router.detect_lang(translated) != language:
        return LLM_DOWN[language]
    return translated


def _is_language_prefix(text: str, language: str) -> bool:
    if router.detect_lang(text) != language:
        return False
    words = set(re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", text.casefold()))
    if len(words) >= 2:
        return True
    markers = {
        "en": {"hello", "hi", "yes", "thanks", "who", "what"},
        "fr": {"bonjour", "oui", "merci", "salut", "je", "le", "la", "les", "ça"},
        "mg": {"salama", "misaotra", "eny", "ahoana", "ianao", "ny"},
    }
    return bool(words & markers[language])


def _compose(question: str, sql: str, columns: list[str], rows: list[tuple],
             notes: list[str], history, language: str = "en") -> str:
    body = format_result(columns, rows, language) if rows else NO_RESULT[language]
    note_text = "\n".join(notes) or {
        "en": "None.", "fr": "Aucune.", "mg": "Tsy misy.",
    }[language]
    candidate = ollama.complete(prompts.render(
        "summary", history=format_history(history or []), question=question, sql=sql or "(aucun)",
        columns=", ".join(column_label(c, language) for c in columns) or "(none)",
        result=body, notes=note_text, language=router.language_name(language)), 300)
    candidate = _ensure_language(candidate, language, "SQL")
    prose = "\n".join(line for line in candidate.splitlines()
                      if not line.lstrip().startswith("|")
                      and not re.fullmatch(r"[\s|:+-]+", line))
    scalar_numbers = numbers_in(body) if len(rows) == len(columns) == 1 else set()
    valid = bool(router.has_useful_content(prose) and grounded(prose, body, note_text)
                 and scalar_numbers <= numbers_in(prose))
    scalar = len(rows) == len(columns) == 1
    if valid:
        summary = prose.strip()
    elif scalar:
        value = rows[0][0]
        if value is None:
            summary = NO_VALUE[language]
        else:
            summary = SINGLE_VALUE[language].format(value=fmt_value(value))
    else:
        summary = RESULTS_CALCULATED[language] if rows else note_text
    parts = [summary]
    if rows and not scalar and (len(rows) > 1 or len(columns) > 1 or not valid):
        parts.append(body)
    if notes and rows:
        note_prefix = {"en": "Note:", "fr": "À noter :", "mg": "Marihina:"}[language]
        parts.append("\n".join(f"{note_prefix} {n}" for n in notes))
    return "\n\n".join(parts)


def _tabular(mode: str, question: str, history, runner, language: str) -> AnswerResult:
    try:
        run = runner()
    except ConfigurationError as exc:
        return AnswerResult(ANALYSIS_DOWN[language], "SQL",
                            raw_result=str(exc), audit_stage="configuration")
    except OutOfRange as exc:
        try:
            text = _compose(question, "", [], [], [str(exc)], history, language)
        except httpx.HTTPError:
            text = OUT_OF_RANGE[language]
        return AnswerResult(text, "SQL", audit_stage="plage de dates")
    except QueryError as exc:
        text = ANALYSIS_ERROR[language]
        return AnswerResult(text, "SQL", exc.sql, exc.details, audit_stage=exc.stage)
    try:
        notes = [_ensure_language(note, language, "SQL note") for note in run.notes]
        text = _compose(question, run.sql, run.columns, run.rows, notes, history, language)
    except httpx.HTTPError as exc:
        return AnswerResult(LLM_DOWN[router.detect_lang(question)], "SQL",
                            run.sql, str(exc)[:300], audit_stage="llm")
    return AnswerResult(
        text, mode, run.sql,
        format_result(run.columns, run.rows, language) if run.rows else NO_RESULT[language],
        notes=tuple(notes),
        data={"columns": [column_label(c, language) for c in run.columns],
              "rows": [[fmt_value(v) for v in r] for r in run.rows]})


def _doc_sources(text: str, sources, language: str) -> str:
    separator = " ; " if language == "fr" else "; "
    citations = separator.join(label for _, label in sources)
    heading = {"en": "Sources:", "fr": "Sources :", "mg": "Loharano:"}[language]
    return f"{text}\n\n{heading} {citations}" if citations else text


def _doc_error(message: str, context: str,
               error: str | None = None, stage: str = "llm") -> AnswerResult:
    excerpts = re.findall(r"(?m)^\[([^\]\n]+)\]\n(.*?)(?=^---\s*$|\Z)", context, re.S)
    lines = [message]
    for label, content in excerpts[:3]:
        content = re.sub(r"(?m)^\[RAG section=[^\]]+\]\s*\n", "", content)
        excerpt_lines = [
            line for raw_line in content.strip().splitlines()
            for line in wrap(raw_line, width=100, break_long_words=False, break_on_hyphens=False)
        ][:3]
        if excerpt_lines:
            lines.append(f"{label}\n" + "\n".join(excerpt_lines))
    return AnswerResult("\n\n".join(lines), "DOCS", raw_result=error, audit_stage=stage)


def _knowledge_attitude_link_polarities(text: str) -> set[str]:
    polarities: set[str] = set()
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text):
        if not any(pattern.search(sentence) for pattern in _KNOWLEDGE_ATTITUDE_LINKS):
            continue
        negative = re.search(
            r"\b(?:no|not|never|without|did not|does not|not found|not observed|"
            r"not established|not investigated|aucun|aucune|pas de|ne\s+\w+\s+pas)\b",
            sentence, re.IGNORECASE)
        polarities.add("negative" if negative else "positive")
    return polarities


def _research_guidance(context: str, language: str) -> str:
    if not _is_research_context(context):
        return ("Réponse concise, selon les extraits." if language == "fr"
                else "Keep the answer concise and use only the excerpts.")
    if language == "fr":
        return (
            "Étude scientifique : privilégie le résumé, les résultats, tableaux et conclusion; "
            "si les deux mesures sont présentes, présente séparément connaissances de transmission "
            "et attitudes. Donne les constats et chiffres utiles sans inventer de valeur. Sépare les scores de connaissance des "
            "attitudes; n'affirme un lien entre eux que si les extraits le rapportent explicitement. "
            "Distingue les résultats de cette étude des lacunes de travaux antérieurs et attribue "
            "précisément les constats (par exemple : « les auteurs rapportent »). Une rareté "
            "d'études est un constat des auteurs sur la littérature antérieure, pas un résultat.")
    return (
        "Research study: prioritize its abstract, Results, tables, key findings and Conclusion; "
        "if both measures are reported, cover transmission knowledge and attitudes separately. "
        "Include relevant findings and figures, but never invent a value. Keep knowledge scores separate from attitudes; "
        "claim a relationship between them only if the excerpts explicitly report it. Distinguish "
        "this study's results from gaps in prior research and attribute claims accurately "
        "(for example, 'the authors report'). A scarcity of prior studies is an author-stated "
        "literature gap, not a result of the present study.")


def _is_research_context(context: str) -> bool:
    return bool(re.search(
        r"\[RAG section=(?:abstract|results|discussion|conclusion)|type=table",
        context, re.IGNORECASE))


def _guard_research_claims(reply: str, context: str, language: str) -> str:
    if not _is_research_context(context):
        return reply
    claims = _knowledge_attitude_link_polarities(reply)
    if not claims:
        return reply
    supported = _knowledge_attitude_link_polarities(context)
    if claims <= supported:
        return reply

    kept = [
        sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", reply)
        if sentence.strip() and not _knowledge_attitude_link_polarities(sentence)
    ]
    warning = (
        "The excerpts report knowledge findings and attitudes separately; "
        "they do not state whether those measures are associated."
        if language == "en" else
        "Ny sombiny dia manasaraka ny fahalalana sy ny fihetsika; tsy milaza izy ireo raha misy fifandraisana."
        if language == "mg" else
        "Les extraits présentent séparément les résultats sur les connaissances et les attitudes; "
        "ils ne précisent pas si ces mesures sont liées.")
    debug_trace("DOCS garde", reason="lien connaissances-attitudes non étayé")
    return " ".join([warning, *kept])


_PERCENTAGE = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*%")


def _guard_research_percentages(reply: str, context: str, language: str) -> str:
    if not _is_research_context(context):
        return reply

    def values(text: str) -> set[Decimal]:
        return {
            Decimal(match.group(1).replace(",", "."))
            for match in _PERCENTAGE.finditer(text)
        }

    supported = values(context)
    if values(reply) <= supported:
        return reply

    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", reply):
        if sentence.strip() and values(sentence) <= supported:
            kept.append(sentence.strip())
    debug_trace("DOCS garde", reason="pourcentage non étayé")
    if kept:
        return " ".join(kept)
    return {
        "en": "The excerpts do not support the stated percentage, so I cannot report it.",
        "fr": "Les extraits ne justifient pas le pourcentage indiqué; je ne peux pas le rapporter.",
        "mg": "Tsy manamarina ilay isan-jato voalaza ny sombiny, ka tsy azoko averina izany.",
    }[language]


def _docs(question: str, lang: str, history, on_docs_wait: Callable[[], None] | None = None,
          on_docs_token: Callable[[str], None] | None = None) -> AnswerResult:
    try:
        context, sources = get_doc_context(question, history, lang)
    except httpx.TimeoutException as exc:
        return _doc_error(LLM_TIMEOUT[lang], "", str(exc)[:300], "llm_timeout")
    except ConfigurationError as exc:
        message = {
            "en": "Document search is not available at the moment.",
            "fr": "La recherche documentaire n'est pas disponible pour le moment.",
            "mg": "Tsy misy amin'izao fotoana izao ny fikarohana antontan-taratasy.",
        }[lang]
        return AnswerResult(message, "DOCS",
                            audit_stage="configuration")
    except Exception as exc:     # table documents_kb absente, base arrêtée… : pas de trace brute
        return AnswerResult(DOCS_DOWN[lang], "DOCS", raw_result=str(exc)[:300],
                            audit_stage="documents")
    if not context:
        debug_trace("DOCS rejet", reason="aucun passage au-dessus du seuil")
        return AnswerResult(NO_DOC[lang], "DOCS")
    prompt = prompts.render("docs", history=format_history(history or []),
                            context=context, question=question,
                            language=router.language_name(lang),
                            research_guidance=_research_guidance(context, lang))
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
            prompt, predict=200,
            emit=(emit_guarded if on_docs_token and research_context
                  else emit_language_safe if on_docs_token else None),
            stage="génération DOCS", num_ctx=4096)
        if buffered_sentence and on_docs_token and research_context:
            guarded = _guard_research_claims(buffered_sentence, context, lang)
            emit_language_safe(_guard_research_percentages(guarded, context, lang))
        clean_reply = _clean_doc_reply(reply)
        clean_reply = _guard_research_claims(clean_reply, context, lang)
        clean_reply = _guard_research_percentages(clean_reply, context, lang)
        verification_started = time.perf_counter()
        detected_lang = router.detect_lang(clean_reply)
        debug_trace(
            "DOCS étape", stage="vérification de langue",
            duration_ms=round((time.perf_counter() - verification_started) * 1000, 2),
            prompt_tokens=ollama.estimate_tokens(clean_reply),
            result_tokens=ollama.estimate_tokens(detected_lang),
            token_count_source="estimated")
        if clean_reply and detected_lang != lang:
            debug_trace("DOCS langue", reason="traduction nécessaire",
                        requested=lang, detected=detected_lang)
            translation = prompts.render(
                "answer_translation", language=router.language_name(lang), answer=clean_reply)
            clean_reply = _clean_doc_reply(ollama.complete(
                translation, 200, temperature=0, stage="traduction de la réponse", num_ctx=4096))
            verification_started = time.perf_counter()
            detected_lang = router.detect_lang(clean_reply)
            debug_trace(
                "DOCS étape", stage="vérification de langue",
                duration_ms=round((time.perf_counter() - verification_started) * 1000, 2),
                prompt_tokens=ollama.estimate_tokens(clean_reply),
                result_tokens=ollama.estimate_tokens(detected_lang),
                token_count_source="estimated")
    except httpx.TimeoutException as exc:
        debug_trace("DOCS rejet", reason="délai de génération dépassé", error=str(exc))
        return _doc_error(LLM_TIMEOUT[lang], context, str(exc)[:300], "llm_timeout")
    except Exception as exc:
        debug_trace("DOCS rejet", reason="échec de génération", error=str(exc))
        return _doc_error(LLM_DOWN[lang], context, str(exc)[:300], "llm")
    if detected_lang != lang:
        debug_trace("DOCS rejet", reason="langue de réponse non conforme",
                    requested=lang, answer=clean_reply)
        return _doc_error(LLM_DOWN[lang], context, stage="response_language")
    if not router.has_useful_content(clean_reply):
        debug_trace("DOCS rejet", reason="filtre de réponse inutile", answer=clean_reply)
        return AnswerResult(_doc_sources(NO_DOC[lang], sources, lang), "DOCS",
                            sources=tuple(sources))
    if on_docs_token and not language_stream_started:
        on_docs_token(clean_reply)
    text = _doc_sources(clean_reply, sources, lang)
    return AnswerResult(text, "DOCS", sources=tuple(sources))


def _clean_doc_reply(reply: str) -> str:
    without_sources = re.sub(r"(?im)^\s*(?:sources?|références?)\s*:\s*.*$", "", reply)
    return re.sub(r"\s*\[[^\]\n]*\]", "", without_sources).strip()


def _general(question: str, original: str, lang: str, history) -> AnswerResult:
    """Pas de streaming ici : la réponse est contrôlée AVANT d'être affichée.
    Le mode chat n'accède ni aux données SQL ni aux documents."""
    summary = router.is_summary_request(question)
    prompt_name = "conversation_summary" if summary else "general"
    prompt = prompts.render(prompt_name, question=question,
                            history=format_history(history or []),
                            language=router.language_name(lang))
    try:
        reply = ollama.complete(prompt, 300, temperature=0.3)
        reply = _ensure_language(reply, lang, "CHAT")
    except Exception as exc:
        return AnswerResult(LLM_DOWN[lang], "CHAT", raw_result=str(exc)[:300],
                            audit_stage="llm")
    guarded = router.guard_general((reply or "").strip(), original, history)
    if guarded != (reply or "").strip():
        debug_trace("CHAT rejet", reason="garde-fou médical ou chiffre non vérifié",
                    question=original, answer=(reply or "").strip())
    return AnswerResult(guarded, "CHAT")


def _answer(question: str, original: str, forced, history,
            decision: router.Route | None, on_docs_wait: Callable[[], None] | None = None,
            on_docs_token: Callable[[str], None] | None = None) -> AnswerResult:
    """Route une question et exécute uniquement l'outil choisi."""
    lang = router.detect_lang(original)
    if forced:
        quick = router.quick_reply(question, allow_chat_replies=False)
        if quick:
            return AnswerResult(_ensure_language(quick[1], lang, "réponse rapide"), "CHAT")
        mode = forced
    else:
        assert decision is not None
        if decision.response:
                return AnswerResult(_ensure_language(decision.response, lang, "réponse rapide"), "CHAT")
        mode = decision.name.upper()
    today = dt.datetime.now(get_settings().tz).date()
    period = parse_period(normalize_question(question), today)
    if mode == "SQL":
        return _tabular("SQL", question, history,
                        lambda: run_sql(question, approved_views(), history, period), lang)
    if mode == "DOCS":
        return _docs(question, lang, history, on_docs_wait, on_docs_token)
    return _general(question, original, lang, history)


def answer(question: str, *, forced: str | None = None, history=None,
           user: str = "inconnu", on_docs_wait: Callable[[], None] | None = None,
           on_docs_token: Callable[[str], None] | None = None) -> AnswerResult:
    question = " ".join(question.split())
    language = router.detect_lang(question)
    if not question:
        return AnswerResult("Please enter a question.", "CHAT")
    if len(question) > get_settings().max_question_chars:
        messages = {
            "en": "Please shorten your question (maximum 2,000 characters).",
            "fr": "Veuillez raccourcir la question (2 000 caractères maximum).",
            "mg": "Fohay kokoa ny fanontanianao azafady (tsy mihoatra ny litera 2 000).",
        }
        return AnswerResult(messages[language], "CHAT")
    if forced and forced not in {"SQL", "DOCS"}:
        raise ValueError("Le mode forcé doit être SQL ou DOCS.")
    debug_trace(
        "Timeouts configurés", ollama_connect_seconds=10, ollama_read_seconds=180,
        ollama_write_seconds=10, ollama_pool_seconds=10, ollama_healthcheck_seconds=3,
        sql_statement_ms=get_settings().sql_timeout_ms, sql_idle_transaction_ms=30000)
    decision = None
    try:
        if forced:
            standalone = router.rewrite_followup(question, history)
        else:
            decision = router.route(question, history)
            standalone = decision.question
    except httpx.TimeoutException as exc:
        result = AnswerResult(LLM_TIMEOUT[language], forced or "CHAT",
                              raw_result=str(exc)[:300], audit_stage="llm_timeout")
        audit(user, question, result.mode, result.audit_stage, None, None)
        return result
    debug_trace("Routage", received=question, rewritten=standalone,
                language=router.detect_lang(question),
                mode=forced or (decision.name.upper() if decision else "CHAT"))
    result = _answer(standalone, question, forced, history, decision,
                     on_docs_wait, on_docs_token)
    shown = question if standalone == question else f"{question} → {standalone}"
    if not router.has_useful_content(result.text):
        debug_trace("Réponse rejetée", reason="filtre de réponse inutile",
                    mode=result.mode, answer=result.text)
        messages = {
            "fr": "Je n'ai pas pu formuler une réponse utile. Pouvez-vous préciser votre demande ?",
            "mg": "Tsy nahavita namorona valiny mahasoa aho. Azafady, hazavao kokoa ny fangatahanao.",
            "en": "I couldn't produce a useful answer. Could you clarify your request?",
        }
        result = replace(result, text=messages[language])
    audit(user, shown, result.mode, result.audit_stage, result.sql,
          len(result.data["rows"]) if result.data else None)
    return result