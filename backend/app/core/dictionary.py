"""Chargement du dictionnaire de données (vues autorisées) et des définitions métier."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.core.errors import ConfigurationError


def _load(path: Path) -> dict:
    if not path.is_file():
        raise ConfigurationError(f"Fichier de configuration introuvable : {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def dictionary() -> dict:
    s = get_settings()
    data, metrics = _load(s.dictionary_path), _load(s.metrics_path)
    if not data.get("views"):
        raise ConfigurationError("Le dictionnaire ne contient aucune vue.")
    data["glossary"] = metrics.get("definitions", {})
    data["undefined_terms"] = metrics.get("undefined_terms", [])
    data["age_groups"] = metrics.get("age_groups", [])
    return data


def approved_views() -> dict[tuple[str, str], dict]:
    """Vues déclarées dans le dictionnaire, limitées aux schémas autorisés."""
    allowed = get_settings().allowed_schemas
    views: dict[tuple[str, str], dict] = {}
    for full, meta in dictionary()["views"].items():
        schema, _, name = full.partition(".")
        if not name or not schema.isidentifier() or not name.isidentifier():
            raise ConfigurationError(f"Nom de vue invalide dans le dictionnaire : {full}")
        if schema.casefold() not in allowed:
            raise ConfigurationError(f"La vue {full} n'est pas dans un schéma autorisé ({sorted(allowed)}).")
        views[(schema.casefold(), name.casefold())] = {**meta, "full": full}
    return views


def undefined_terms() -> list[dict]:
    try:
        return dictionary().get("undefined_terms") or []
    except ConfigurationError:
        return []
