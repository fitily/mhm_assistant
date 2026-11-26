"""Fetch, normalize, and briefly cache public health news feeds."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, time as day_start, timedelta, timezone
from typing import Callable

import httpx

from app.core.config import get_settings
from app.domain.feeds.parser import parse_journal_feed, parse_who_afro_updates, parse_who_news

log = logging.getLogger("mhm.feeds")

_TIMEOUT = httpx.Timeout(8.0, connect=3.0)
_CACHE_TTL_SECONDS = 300
NEWS_WINDOW_DAYS = 7                           # seul l'affichage est limité : le cache garde tout ce que les sources renvoient
_FUTURE_TOLERANCE = timedelta(minutes=15)      # petite marge pour un décalage d'horloge entre une source et nous
_MAX_SOURCE_BYTES = 2_000_000
_CACHE: tuple[float, dict] | None = None
_CACHE_LOCK = asyncio.Lock()


class FeedsUnavailableError(Exception):
    """Raised when every configured public news source is unavailable."""


def clear_cache() -> None:
    global _CACHE
    _CACHE = None


async def _get_text(client: httpx.AsyncClient, url: str) -> str:
    chunks = []
    size = 0
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > _MAX_SOURCE_BYTES:
                raise ValueError("News source response exceeded the size limit.")
            chunks.append(chunk)
        return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


async def _fetch_source(
    client: httpx.AsyncClient,
    *,
    key: str,
    label: str,
    url: str,
    parse: Callable[[str], list[dict]],
) -> tuple[dict, list[dict]]:
    content = await _get_text(client, url)
    return {"key": key, "label": label, "url": url, "connected": True}, parse(content)


async def _fetch_all() -> dict:
    global _CACHE
    sources = (
        {
            "key": "who",
            "label": "WHO",
            "url": "https://www.who.int/news",
            "parse": parse_who_news,
        },
        {
            "key": "who-africa",
            "label": "WHO Africa",
            "url": "https://www.afro.who.int/outbreaks-and-emergencies-updates",
            "parse": parse_who_afro_updates,
        },
        {
            "key": "lancet",
            "label": "The Lancet",
            "url": "https://www.thelancet.com/rssfeed/lancet_online.xml",
            "parse": lambda content: parse_journal_feed(
                content, source="The Lancet", host="thelancet.com"
            ),
        },
        {
            "key": "nejm",
            "label": "NEJM",
            "url": "https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm",
            "parse": lambda content: parse_journal_feed(content, source="NEJM", host="nejm.org"),
        },
    )
    headers = {
        "User-Agent": "MHM-Ambovo-Health-News/1.0",
        "Accept": "text/html, application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True, headers=headers) as client:
        results = await asyncio.gather(
            *(
                _fetch_source(
                    client,
                    key=source["key"],
                    label=source["label"],
                    url=source["url"],
                    parse=source["parse"],
                )
                for source in sources
            ),
            return_exceptions=True,
        )

    articles: list[dict] = []
    source_states = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            log.warning("News source %s is unavailable (%s).", source["key"], type(result).__name__)
            source_states.append({
                "key": source["key"],
                "label": source["label"],
                "url": source["url"],
                "connected": False,
            })
            continue
        source_state, source_articles = result
        source_states.append(source_state)
        articles.extend(source_articles)

    if not any(source["connected"] for source in source_states):
        raise FeedsUnavailableError("No health news source could be reached.")

    unique_articles = {article["url"]: article for article in articles}
    articles = sorted(
        unique_articles.values(),
        key=lambda article: article["published_at"] or "",
        reverse=True,
    )
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "items": articles,
        "updated_at": now,
        "connected": all(source["connected"] for source in source_states),
        "sources": source_states,
    }
    if result["connected"]:
        _CACHE = (time.monotonic() + _CACHE_TTL_SECONDS, result)
    return result


async def get_news() -> dict:
    if _CACHE and _CACHE[0] > time.monotonic():
        return _CACHE[1]
    async with _CACHE_LOCK:
        if _CACHE and _CACHE[0] > time.monotonic():
            return _CACHE[1]
        return await _fetch_all()


def news_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Période affichée, en UTC : de minuit (fuseau de l'application) il y a 7 jours jusqu'à maintenant.

    Recalculée à chaque appel : elle suit donc la date de consultation, même quand les articles viennent du cache.
    Partir de minuit évite qu'un article daté du jour J (les sources OMS ne donnent souvent que la date) disparaisse
    en cours de journée J+7.
    """
    tz = get_settings().tz
    local_now = (now or datetime.now(timezone.utc)).astimezone(tz)
    start = datetime.combine(local_now.date() - timedelta(days=NEWS_WINDOW_DAYS), day_start.min, tzinfo=tz)
    return start.astimezone(timezone.utc), local_now.astimezone(timezone.utc) + _FUTURE_TOLERANCE


def _published(article: dict) -> datetime | None:
    """Date de publication de l'article (UTC), ou None si absente ou illisible."""
    value = article.get("published_at")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def filter_news(payload: dict, *, category: str, query: str, now: datetime | None = None) -> dict:
    """Garde les articles PUBLIÉS pendant la période (date de publication de la source), puis applique catégorie et recherche.

    Sans date lisible, un article est écarté : on ne peut pas prouver qu'il est récent.
    """
    start, end = news_window(now)
    terms = query.casefold().split()
    items = []
    for item in payload["items"]:
        published = _published(item)
        if published is None or not (start <= published <= end):
            continue
        if category != "all" and item["category"] != category:
            continue
        if all(term in f'{item["title"]} {item["summary"]} {item["source"]}'.casefold() for term in terms):
            items.append(item)
    return {**payload, "items": items, "window_days": NEWS_WINDOW_DAYS, "since": start.isoformat()}
