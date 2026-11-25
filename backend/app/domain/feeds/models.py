"""Modèles du domaine « veille » : un article de flux et la description d'une source."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class FeedFetchError(Exception):
    """La source n'a pas pu être téléchargée (réseau, statut HTTP, taille)."""


class FeedParseError(Exception):
    """Le contenu reçu n'est pas un flux RSS/Atom exploitable (ou il est dangereux)."""


@dataclass(frozen=True)
class FeedItem:
    id: str
    title: str
    summary: str
    url: str
    published_at: datetime | None
    source_id: str
    source_name: str
    tag: str | None = None  # ex. « alerte » pour les urgences sanitaires


@dataclass(frozen=True)
class FeedSource:
    id: str
    name: str
    group: str                       # « news » ou « research »
    urls: tuple[str, ...]            # flux RSS/Atom ; les résultats de tous les flux sont fusionnés
    tag: str | None = None
    pubmed_term: str | None = None   # requête PubMed de secours si aucun flux ne répond
