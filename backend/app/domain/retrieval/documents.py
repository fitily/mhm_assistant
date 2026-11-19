"""Recherche vectorielle et assemblage des passages documentaires."""
from __future__ import annotations

import time

import httpx

from app.core.config import debug_trace, get_settings
from app.domain import prompts
from app.domain.formatting import format_history
from app.infrastructure.db import vectors
from app.domain.retrieval.ranking import (
    _SECTION_MARKER,
    _rank_hits,
    _relevant_excerpt,
    _section_info,
)
from app.infrastructure.llm import ollama


def _english_query(question: str, history, language: str) -> str:
    if language == "en":
        return question
    prompt = prompts.render(
        "search_query",
        question=question,
        history=format_history(history or []),
    )
    try:
        query = ollama.complete(
            prompt,
            predict=80,
            temperature=0,
            stage="traduction de la requête",
        ).strip().strip("\"'")
    except httpx.TimeoutException:
        raise
    except httpx.HTTPError as exc:
        debug_trace("RAG traduction", reason="échec de traduction", error=str(exc))
        return question
    return query[:500] if query else question


def get_doc_context(
    question: str,
    history=None,
    language: str = "en",
) -> tuple[str, list[tuple[float, str]]]:
    """Retourne (contexte pour le prompt, sources[(score, « fichier - page N »)])."""
    settings = get_settings()
    query = _english_query(question, history, language)
    vector = ollama.embed([query], stage="embedding")[0]
    search_started = time.perf_counter()
    candidate_count = min(max(settings.top_k * 6, 32), 48)
    retrieved = vectors.similar(vector, candidate_count)
    debug_trace(
        "RAG recherche",
        duration_ms=round((time.perf_counter() - search_started) * 1000, 2),
        prompt_tokens=ollama.estimate_tokens(query),
        result_tokens=len(retrieved),
    )
    debug_trace(
        "RAG passages",
        question=question,
        search_query=query,
        language=language,
        threshold=settings.min_score,
        passages=[{
            "score": float(hit["score"]),
            "file": hit["file_name"],
            "page": hit["page"],
            "content": hit["content"],
            "accepted": hit["score"] >= settings.min_score,
            "rejection": None if hit["score"] >= settings.min_score else "seuil de similarité",
        } for hit in retrieved],
    )
    accepted = [hit for hit in retrieved if hit["score"] >= settings.min_score]
    primary_file = retrieved[0]["file_name"] if retrieved else None
    primary_research = any(
        hit["file_name"] == primary_file
        and _section_info(hit)[0] in {
            "abstract", "results", "results_discussion", "discussion", "conclusion",
        }
        for hit in retrieved
    )
    if primary_research:
        expanded_query = f"{query} public awareness stigmatizing attitudes results tables"
        research_started = time.perf_counter()
        research_vector = ollama.embed(
            [expanded_query],
            stage="embedding des résultats de l'étude",
        )[0]
        research_hits = vectors.similar(research_vector, candidate_count)
        debug_trace(
            "RAG recherche résultats",
            duration_ms=round((time.perf_counter() - research_started) * 1000, 2),
            prompt_tokens=ollama.estimate_tokens(expanded_query),
            result_tokens=len(research_hits),
        )
        merged: dict[tuple[str, int | None, str], dict] = {}
        for hit in retrieved + research_hits:
            key = (hit["file_name"], hit["page"], hit["content"])
            existing = merged.get(key)
            if existing is None:
                merged[key] = dict(hit)
            else:
                existing["score"] = max(float(existing["score"]), float(hit["score"]))
        retrieved = list(merged.values())
        accepted = [hit for hit in retrieved if hit["score"] >= settings.min_score]
        secondary_floor = max(0.0, settings.min_score - 0.10)
        accepted.extend(
            hit for hit in retrieved
            if hit["file_name"] == primary_file
            and hit["score"] >= secondary_floor
            and _section_info(hit)[0] in {
                "abstract", "results", "results_discussion", "discussion", "conclusion",
            }
            and hit not in accepted
        )

    hits, research_source = _rank_hits(accepted, 3)
    debug_trace(
        "RAG reclassement",
        research_source=research_source,
        selected=[{
            "file": hit["file_name"],
            "page": hit["page"],
            "section": _section_info(hit)[0],
            "type": _section_info(hit)[1],
            "table": _section_info(hit)[2],
            "score": float(hit["score"]),
        } for hit in hits],
    )
    if not hits:
        debug_trace("RAG rejet", reason="seuil de similarité", threshold=settings.min_score)
        return "", []

    parts, sources, seen = [], [], set()
    size = len("EXTRAITS :\n")
    for hit in hits:
        page = hit["page"] if hit["page"] is not None else "?"
        label = f"{hit['file_name']} - page {page}"
        section, kind, table_id = _section_info(hit)
        content = hit["content"]
        if not _SECTION_MARKER.match(content):
            marker = f"[RAG section={section} type={kind}"
            if table_id:
                marker += f" table={table_id}"
            content = f"{marker}]\n{content}"
        excerpt = _relevant_excerpt(content, query)
        part = f"[{label}]\n{excerpt}"
        if size + len(part) + 5 > settings.max_context_chars:
            remaining = settings.max_context_chars - size
            if remaining <= len(f"[{label}]\n"):
                break
            part = part[:remaining]
        parts.append(part)
        size += len(part) + 5
        if label not in seen:
            seen.add(label)
            sources.append((float(hit["score"]), label))
        if size >= settings.max_context_chars:
            break
    return "EXTRAITS :\n" + "\n---\n".join(parts) + "\n", sources
