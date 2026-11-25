"""Agrégation des flux de veille avec cache.

- Cache mémoire par source (durée `FEED_CACHE_TTL_S`) : les médecins ne déclenchent pas un
  téléchargement à chaque ouverture de page, et les sites sources ne sont pas sollicités en rafale.
- Si une source tombe, on garde les derniers articles connus (statut « stale ») au lieu d'une page vide.
- Une source en échec n'est pas réinterrogée avant 60 s ; le bouton « Actualiser » est limité à 1 fois / 30 s.
- Les téléchargements d'un même groupe se font en parallèle.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import debug_trace, get_settings
from app.domain.feeds.models import FeedFetchError, FeedItem, FeedParseError, FeedSource
from app.domain.feeds.parser import parse_feed
from app.domain.feeds.sources import NEWS, RESEARCH, load_sources
from app.infrastructure.feeds import client, pubmed

ERROR_RETRY_S = 60
MIN_FORCED_REFRESH_S = 30
GROUP_LIMITS = {NEWS: 30, RESEARCH: 24}
_FAR_PAST = datetime.min.replace(tzinfo=UTC)


@dataclass
class _Entry:
    items: list[FeedItem]
    status: str                    # ok | stale | error
    via: str | None                # rss | pubmed
    fetched_at: datetime | None
    checked_at: float


@dataclass(frozen=True)
class SourceReport:
    id: str
    name: str
    status: str
    via: str | None
    fetched_at: datetime | None
    count: int


@dataclass(frozen=True)
class FeedBundle:
    items: list[FeedItem]
    sources: list[SourceReport]
    generated_at: datetime


@dataclass
class FeedAggregator:
    sources: tuple[FeedSource, ...] = field(default_factory=load_sources)
    fetch: Callable[..., bytes] = client.fetch_bytes
    fetch_pubmed: Callable[..., list[FeedItem]] = pubmed.latest
    clock: Callable[[], float] = time.monotonic
    _cache: dict[str, _Entry] = field(default_factory=dict)
    _locks: dict[str, threading.Lock] = field(default_factory=dict)

    # --- API publique ---------------------------------------------------------------------
    def get_group(self, group: str, *, refresh: bool = False) -> FeedBundle:
        selected = [s for s in self.sources if s.group == group]
        if not selected:
            return FeedBundle([], [], datetime.now(UTC))
        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            entries = list(pool.map(lambda s: self._load(s, refresh), selected))

        merged: dict[str, FeedItem] = {}
        for entry in entries:
            for item in entry.items:
                merged.setdefault(item.url, item)
        ordered = sorted(merged.values(), key=lambda i: i.published_at or _FAR_PAST, reverse=True)
        reports = [
            SourceReport(s.id, s.name, e.status, e.via, e.fetched_at, len(e.items))
            for s, e in zip(selected, entries, strict=True)]
        return FeedBundle(ordered[: GROUP_LIMITS.get(group, 30)], reports, datetime.now(UTC))

    def clear(self) -> None:
        self._cache.clear()

    # --- interne --------------------------------------------------------------------------
    def _load(self, source: FeedSource, force: bool) -> _Entry:
        lock = self._locks.setdefault(source.id, threading.Lock())
        with lock:
            entry = self._cache.get(source.id)
            if entry and self._is_fresh(entry, force):
                return entry
            entry = self._refresh(source, entry)
            self._cache[source.id] = entry
            return entry

    def _is_fresh(self, entry: _Entry, force: bool) -> bool:
        age = self.clock() - entry.checked_at
        if force:
            return age < MIN_FORCED_REFRESH_S
        ttl = get_settings().feed_cache_ttl_s if entry.status == "ok" else ERROR_RETRY_S
        return age < ttl

    def _refresh(self, source: FeedSource, previous: _Entry | None) -> _Entry:
        settings = get_settings()
        per_source = settings.feed_max_items_per_source
        items: list[FeedItem] = []
        via = "rss"
        for url in source.urls:
            try:
                content = self.fetch(url, timeout=settings.feed_timeout_s)
                items += parse_feed(content, source_id=source.id, source_name=source.name,
                                    tag=source.tag, limit=per_source)
            except (FeedFetchError, FeedParseError) as exc:
                debug_trace("flux indisponible", source=source.id, url=url, error=str(exc))

        if not items and source.pubmed_term:
            try:
                items = self.fetch_pubmed(
                    source.pubmed_term, source_id=source.id, source_name=source.name,
                    limit=per_source, timeout=settings.feed_timeout_s)
                via = "pubmed"
            except FeedFetchError as exc:
                debug_trace("PubMed indisponible", source=source.id, error=str(exc))

        now = datetime.now(UTC)
        if items:
            unique = {i.url: i for i in items}.values()
            kept = sorted(unique, key=lambda i: i.published_at or _FAR_PAST, reverse=True)[:per_source]
            return _Entry(list(kept), "ok", via, now, self.clock())
        if previous and previous.items:
            return _Entry(previous.items, "stale", previous.via, previous.fetched_at, self.clock())
        return _Entry([], "error", None, None, self.clock())


aggregator = FeedAggregator()


def get_aggregator() -> FeedAggregator:
    return aggregator
