"""Grounding rules for scientific claims in document answers."""
from __future__ import annotations

import re
from decimal import Decimal

from app.core.config import debug_trace


_KNOWLEDGE = (
    r"(?:(?:hiv(?:\s+transmission)?\s+)?knowledge"
    r"(?:\s+(?:scores?|levels?))?|connaissances?)"
)
_ATTITUDES = r"(?:(?:stigmatizing\s+|stigmatisantes?\s+)?attitudes?)"
_RELATION = (
    r"(?:correlat\w*|associat\w*|relationship|links?|related|"
    r"corrélation|relations?|liens?)"
)
_KNOWLEDGE_ATTITUDE_LINKS = (
    re.compile(
        rf"{_RELATION}.{{0,30}}(?:between|among|entre)\s+(?:the\s+)?{_KNOWLEDGE}"
        rf".{{0,50}}(?:and|with|et)\s+(?:the\s+)?{_ATTITUDES}",
        re.I,
    ),
    re.compile(
        rf"(?:{_KNOWLEDGE}).{{0,40}}(?:correlat\w*|associat\w*|linked|related|li[eé]s?)"
        rf".{{0,30}}(?:to|with|à|aux|avec)\s+(?:the\s+)?{_ATTITUDES}",
        re.I,
    ),
    re.compile(
        rf"(?:{_ATTITUDES}).{{0,40}}(?:correlat\w*|associat\w*|linked|related|li[eé]s?)"
        rf".{{0,30}}(?:to|with|à|aux|avec)\s+(?:the\s+)?{_KNOWLEDGE}",
        re.I,
    ),
    re.compile(
        rf"(?:{_KNOWLEDGE}).{{0,25}}(?:and|&|et).{{0,25}}(?:{_ATTITUDES})"
        rf".{{0,25}}(?:are|were|is|was|sont|étaient)?\s*"
        rf"(?:(?:not|never|pas)\s+)?"
        rf"(?:(?:significantly|strongly|statistically|positively|negatively)\s+)?"
        rf"(?:correlat\w*|associat\w*|related|linked|li[eé]s?)",
        re.I,
    ),
)
_PERCENTAGE = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*%")


def _knowledge_attitude_link_polarities(text: str) -> set[str]:
    polarities: set[str] = set()
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text):
        if not any(pattern.search(sentence) for pattern in _KNOWLEDGE_ATTITUDE_LINKS):
            continue
        negative = re.search(
            r"\b(?:no|not|never|without|did not|does not|not found|not observed|"
            r"not established|not investigated|aucun|aucune|pas de|ne\s+\w+\s+pas)\b",
            sentence,
            re.IGNORECASE,
        )
        polarities.add("negative" if negative else "positive")
    return polarities


def _is_research_context(context: str) -> bool:
    return bool(re.search(
        r"\[RAG section=(?:abstract|results|discussion|conclusion)|type=table",
        context,
        re.IGNORECASE,
    ))


def _research_guidance(context: str, language: str) -> str:
    if not _is_research_context(context):
        return (
            "Réponse concise, selon les extraits."
            if language == "fr"
            else "Keep the answer concise and use only the excerpts."
        )
    if language == "fr":
        return (
            "Étude scientifique : privilégie le résumé, les résultats, tableaux et conclusion; "
            "si les deux mesures sont présentes, présente séparément connaissances de transmission "
            "et attitudes. Donne les constats et chiffres utiles sans inventer de valeur. Sépare les "
            "scores de connaissance des attitudes; n'affirme un lien entre eux que si les extraits "
            "le rapportent explicitement. Distingue les résultats de cette étude des lacunes de "
            "travaux antérieurs et attribue précisément les constats (par exemple : « les auteurs "
            "rapportent »). Une rareté d'études est un constat des auteurs sur la littérature "
            "antérieure, pas un résultat."
        )
    return (
        "Research study: prioritize its abstract, Results, tables, key findings and Conclusion; "
        "if both measures are reported, cover transmission knowledge and attitudes separately. "
        "Include relevant findings and figures, but never invent a value. Keep knowledge scores "
        "separate from attitudes; claim a relationship between them only if the excerpts explicitly "
        "report it. Distinguish this study's results from gaps in prior research and attribute "
        "claims accurately (for example, 'the authors report'). A scarcity of prior studies is an "
        "author-stated literature gap, not a result of the present study."
    )


def _guard_research_claims(reply: str, context: str, language: str) -> str:
    if not _is_research_context(context):
        return reply
    claims = _knowledge_attitude_link_polarities(reply)
    if not claims:
        return reply
    if claims <= _knowledge_attitude_link_polarities(context):
        return reply

    kept = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", reply)
        if sentence.strip() and not _knowledge_attitude_link_polarities(sentence)
    ]
    warning = (
        "The excerpts report knowledge findings and attitudes separately; "
        "they do not state whether those measures are associated."
        if language == "en"
        else "Ny sombiny dia manasaraka ny fahalalana sy ny fihetsika; tsy milaza izy ireo raha misy fifandraisana."
        if language == "mg"
        else "Les extraits présentent séparément les résultats sur les connaissances et les attitudes; "
        "ils ne précisent pas si ces mesures sont liées."
    )
    debug_trace("DOCS garde", reason="lien connaissances-attitudes non étayé")
    return " ".join([warning, *kept])


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
