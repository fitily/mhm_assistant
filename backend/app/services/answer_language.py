"""Language checks and answer translation shared by response generators."""
from __future__ import annotations

import re

from app.domain import prompts, router
from app.infrastructure.llm import ollama
from app.services.answer_messages import LLM_DOWN


def _ensure_language(text: str, language: str, stage: str) -> str:
    if not text.strip() or router.detect_lang(text) == language:
        return text
    prompt = prompts.render(
        "answer_translation",
        language=router.language_name(language),
        answer=text,
    )
    translated = ollama.complete(
        prompt,
        max(200, ollama.estimate_tokens(text) + 60),
        temperature=0,
        stage=f"traduction {stage}",
    ).strip()
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
