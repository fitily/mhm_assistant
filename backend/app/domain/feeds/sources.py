"""Catalogue des sources de veille.

Les adresses de flux sont des valeurs par défaut : chaque source peut être redéfinie dans `.env`
avec `FEED_URLS_<ID>` (adresses séparées par des virgules), sans toucher au code. Exemple :
    FEED_URLS_WHO=https://www.who.int/rss-feeds/news-english.xml
"""
from __future__ import annotations

import os

from app.domain.feeds.models import FeedSource

NEWS = "news"
RESEARCH = "research"

_DEFAULT_SOURCES: tuple[FeedSource, ...] = (
    FeedSource(
        id="who", name="OMS", group=NEWS,
        urls=("https://www.who.int/rss-feeds/news-english.xml",
              "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml")),
    FeedSource(
        id="afro", name="OMS Afrique", group=NEWS, tag="alerte",
        urls=("https://www.afro.who.int/rss/emergencies.xml",)),
    FeedSource(
        id="lancet", name="The Lancet", group=RESEARCH,
        urls=("https://www.thelancet.com/rssfeed/lancet_online.xml",
              "https://www.thelancet.com/rssfeed/lancet_current.xml"),
        pubmed_term='"Lancet"[ta]'),
    FeedSource(
        id="nejm", name="NEJM", group=RESEARCH,
        urls=("https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss",),
        pubmed_term='"N Engl J Med"[ta]'),
)


def _override(source: FeedSource) -> FeedSource:
    raw = os.getenv(f"FEED_URLS_{source.id.upper()}", "")
    urls = tuple(u.strip() for u in raw.split(",") if u.strip().startswith(("http://", "https://")))
    if not urls:
        return source
    return FeedSource(source.id, source.name, source.group, urls, source.tag, source.pubmed_term)


def load_sources() -> tuple[FeedSource, ...]:
    return tuple(_override(s) for s in _DEFAULT_SOURCES)
