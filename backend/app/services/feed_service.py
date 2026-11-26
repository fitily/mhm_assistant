"""Fetch, normalize, and briefly cache public health news feeds."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Callable

import httpx

from app.domain.feeds.parser import parse_journal_feed, parse_who_afro_updates, parse_who_news

log = logging.getLogger("mhm.feeds")

_TIMEOUT = httpx.Timeout(8.0, connect=3.0)
_CACHE_TTL_SECONDS = 300
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


def filter_news(payload: dict, *, category: str, query: str) -> dict:
    terms = query.casefold().split()
    items = [
        item for item in payload["items"]
        if (category == "all" or item["category"] == category)
        and all(
            term in f'{item["title"]} {item["summary"]} {item["source"]}'.casefold()
            for term in terms
        )
    ]
    return {**payload, "items": items}
