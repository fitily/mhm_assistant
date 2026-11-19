"""Section-aware ranking of retrieved document excerpts."""
from __future__ import annotations

import re


_SECTION_MARKER = re.compile(
    r"^\[RAG section=(?P<section>[a-z_]+) type=(?P<kind>[a-z_]+)"
    r"(?: table=(?P<table>[a-z0-9]+))?\]",
    re.IGNORECASE,
)
_SECTION_BOOST = {
    "abstract": 0.12,
    "results": 0.17,
    "results_discussion": 0.15,
    "discussion": 0.10,
    "conclusion": 0.10,
    "introduction": -0.10,
    "methods": -0.05,
    "references": -0.20,
}


def _relevant_excerpt(content: str, question: str, limit: int = 600) -> str:
    metadata = re.match(r"(\[RAG section=[^\]]+\]\n)", content)
    prefix = metadata.group(1) if metadata else ""
    body = content[len(prefix):]
    if metadata:
        section_info = _SECTION_MARKER.match(content)
        if section_info and section_info.group("section").casefold() in {
            "abstract", "conclusion",
        }:
            question += " results findings awareness transmission knowledge attitudes stigma"
        elif section_info and section_info.group("kind").casefold() == "table":
            question += " findings awareness transmission knowledge attitudes stigma misconceptions"
    excerpt_limit = max(1, limit - len(prefix))
    if len(body) <= excerpt_limit:
        return prefix + body
    terms = {
        word.casefold() for word in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", question)
        if len(word) > 2
    }
    sentences = list(re.finditer(r"[^.!?;\n]+(?:[.!?;]+|$)", body))
    section_info = _SECTION_MARKER.match(content)
    abstract_results = (
        re.search(r"\bresults?\s*:", body, re.IGNORECASE)
        if section_info and section_info.group("section").casefold() == "abstract"
        else None
    )
    if abstract_results:
        start = abstract_results.start()
    else:
        best = max(
            sentences,
            key=lambda match: len(
                terms & {
                    word.casefold()
                    for word in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", match.group())
                }
            ),
            default=None,
        )
        if best is None:
            start = 0
        else:
            center = (best.start() + best.end()) // 2
            start = max(0, min(len(body) - excerpt_limit, center - excerpt_limit // 2))
    prefix_ellipsis = "…" if start else ""
    suffix_ellipsis = "…" if start + excerpt_limit < len(body) else ""
    excerpt_length = excerpt_limit - len(prefix_ellipsis) - len(suffix_ellipsis)
    excerpt = body[start:start + excerpt_length].strip()
    return f"{metadata.group(1) if metadata else ''}{prefix_ellipsis}{excerpt}{suffix_ellipsis}"


def _section_info(hit: dict) -> tuple[str, str, str | None]:
    content = hit["content"]
    match = _SECTION_MARKER.match(content)
    if match:
        return (
            match.group("section").casefold(),
            match.group("kind").casefold(),
            match.group("table"),
        )
    sample = content[:700]
    if len(re.findall(r"\b(?:PMID|doi\.org/)\b", sample, re.IGNORECASE)) >= 2:
        return "references", "prose", None
    table_captions = list(re.finditer(
        r"\btable\s*(?P<table>\d+|[ivxlcdm]+)\s*[.:]\s+[A-Z]",
        sample,
        re.IGNORECASE,
    ))
    if table_captions:
        return "results", "table", table_captions[-1].group("table").casefold()
    if re.search(
        r"\btable\s+\d+\s+(?:shows|illustrates|indicates|demonstrates)\b",
        sample,
        re.IGNORECASE,
    ):
        return "results", "prose", None
    heading = re.search(
        r"\b\d+(?:\.\d+)*[.)]?\s+"
        r"(?P<section>abstract|introduction|results?|findings|discussion|"
        r"conclusions?|references)\b",
        sample,
        re.IGNORECASE,
    )
    if not heading:
        heading = re.match(
            r"\s*(?P<section>abstract|results?|findings|discussion|"
            r"conclusions?|references)\b",
            sample,
            re.IGNORECASE,
        )
    if heading:
        section = heading.group("section").casefold()
        if section in {"result", "findings"}:
            section = "results"
        elif section == "conclusions":
            section = "conclusion"
        elif section == "references":
            section = "references"
        return section, "prose", None
    return "body", "prose", None


def _is_demographic_table(hit: dict) -> bool:
    _, kind, table = _section_info(hit)
    return (
        kind == "table"
        and table == "1"
        and bool(re.search(
            r"\b(?:demographic(?:s| profile)?|participant characteristics|"
            r"nationality|marital status|education level|economic status)\b",
            hit["content"][:700],
            re.IGNORECASE,
        ))
    )


def _rank_hits(retrieved: list[dict], count: int) -> tuple[list[dict], bool]:
    if not retrieved:
        return [], False
    primary_file = retrieved[0]["file_name"]
    research_sections = {
        "abstract", "results", "results_discussion", "discussion", "conclusion", "table",
    }
    is_primary_study = any(
        hit["file_name"] == primary_file
        and (
            _section_info(hit)[0] in research_sections
            or _section_info(hit)[1] == "table"
        )
        for hit in retrieved
    )

    def adjusted_score(hit: dict) -> float:
        score = float(hit["score"])
        if not is_primary_study:
            return score
        section, kind, _ = _section_info(hit)
        if hit["file_name"] != primary_file:
            return score - 0.12
        table_boost = 0.03 if kind == "table" else 0
        demographic_penalty = 0.15 if _is_demographic_table(hit) else 0
        return score + _SECTION_BOOST.get(section, 0) + table_boost - demographic_penalty

    ordered = sorted(retrieved, key=adjusted_score, reverse=True)
    if not is_primary_study:
        return ordered[:count], False

    chosen: list[dict] = []
    primary_findings = [
        hit for hit in ordered
        if hit["file_name"] == primary_file
        and (
            _section_info(hit)[0] in {"results", "results_discussion"}
            or _section_info(hit)[1] == "table"
        )
        and not _is_demographic_table(hit)
    ]
    if primary_findings:
        chosen.append(primary_findings[0])
        first_section, first_kind, first_table = _section_info(primary_findings[0])
        first_family = f"table:{first_table}" if first_kind == "table" else first_section

        def family(hit: dict) -> str:
            section, kind, table = _section_info(hit)
            return f"table:{table}" if kind == "table" else section

        second = next(
            (hit for hit in primary_findings[1:] if family(hit) != first_family),
            None,
        )
        if second:
            chosen.append(second)

    study_summary = next(
        (
            hit for hit in ordered
            if hit["file_name"] == primary_file
            and _section_info(hit)[0] in {"abstract", "conclusion"}
        ),
        None,
    )
    if study_summary and study_summary not in chosen:
        chosen.append(study_summary)
    if len(chosen) < count:
        for hit in ordered:
            section, _, _ = _section_info(hit)
            if (
                hit["file_name"] == primary_file
                and section in {
                    "abstract", "results", "results_discussion", "discussion", "conclusion",
                }
                and not _is_demographic_table(hit)
                and hit not in chosen
            ):
                chosen.append(hit)
            if len(chosen) == count:
                break
    return chosen[:count], True
