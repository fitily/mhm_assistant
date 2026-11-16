"""Chargement des modèles de prompts depuis config/prompts/*.txt."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import ASSISTANT_NAME, get_settings


@lru_cache(maxsize=None)
def _template(name: str) -> str:
    return (get_settings().prompts_dir / f"{name}.txt").read_text(encoding="utf-8")


def render(name: str, **values) -> str:
    values.setdefault("assistant_name", ASSISTANT_NAME)
    prompt = _template(name).format(**values)
    if name in {"summary", "docs", "general", "conversation_summary"}:
        return _template("system").format(**values) + "\n\n" + prompt
    return prompt
