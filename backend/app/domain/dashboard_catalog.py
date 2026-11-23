"""Catalogue contrôlé des dashboards Superset (config/dashboards.yaml).

Règle de sécurité : on ne manipule que des « clés » du catalogue. Une clé inconnue est refusée,
le chat et le navigateur ne peuvent donc jamais faire ouvrir un autre dashboard.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.core.errors import ConfigurationError

_KEY = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")


class UnknownDashboard(LookupError):
    """La clé demandée n'existe pas dans le catalogue."""


@dataclass(frozen=True)
class Dashboard:
    key: str
    title: str
    uuid: str
    description: str = ""
    keywords: tuple[str, ...] = ()  # mots par lesquels l'utilisateur peut désigner ce dashboard dans le chat


class DashboardCatalog:
    def __init__(self, dashboards: list[Dashboard]):
        keys = [d.key for d in dashboards]
        uuids = [d.uuid for d in dashboards]
        if len(set(keys)) != len(keys):
            raise ConfigurationError("dashboards.yaml : deux dashboards ont la même clé.")
        if len(set(uuids)) != len(uuids):
            raise ConfigurationError("dashboards.yaml : deux dashboards ont le même UUID.")
        self._by_key = {d.key: d for d in dashboards}

    def all(self) -> list[Dashboard]:
        return list(self._by_key.values())

    def get(self, key: str) -> Dashboard:
        try:
            return self._by_key[key]
        except KeyError:
            raise UnknownDashboard(key) from None

    @classmethod
    def from_file(cls, path: Path) -> "DashboardCatalog":
        try:
            raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            raise ConfigurationError(f"Catalogue de dashboards introuvable : {path}") from None
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"dashboards.yaml illisible : {exc}") from None

        items = raw.get("dashboards") or []
        if not isinstance(items, list):
            raise ConfigurationError("dashboards.yaml : « dashboards » doit être une liste.")
        return cls([_parse(item, i) for i, item in enumerate(items, start=1)])


def _parse(item, position: int) -> Dashboard:
    if not isinstance(item, dict):
        raise ConfigurationError(f"dashboards.yaml : l'entrée n°{position} est invalide.")
    key = str(item.get("key", "")).strip()
    title = str(item.get("title", "")).strip()
    raw_uuid = str(item.get("uuid", "")).strip()
    if not _KEY.match(key):
        raise ConfigurationError(
            f"dashboards.yaml : clé invalide « {key} » (minuscules, chiffres, - ou _, 2 à 31 caractères)."
        )
    if not title:
        raise ConfigurationError(f"dashboards.yaml : le dashboard « {key} » n'a pas de titre.")
    try:
        normalized = str(uuid.UUID(raw_uuid))
    except ValueError:
        raise ConfigurationError(f"dashboards.yaml : UUID invalide pour « {key} ».") from None
    raw_keywords = item.get("keywords") or []
    if not isinstance(raw_keywords, list):
        raise ConfigurationError(f"dashboards.yaml : « keywords » de « {key} » doit être une liste.")
    keywords = tuple(str(k).strip() for k in raw_keywords if str(k).strip())
    return Dashboard(key=key, title=title, uuid=normalized,
                     description=str(item.get("description", "")).strip(), keywords=keywords)


@lru_cache(maxsize=1)
def get_catalog() -> DashboardCatalog:
    return DashboardCatalog.from_file(get_settings().dashboards_path)
