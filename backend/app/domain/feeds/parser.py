"""Lecture de flux RSS 2.0, RSS 1.0 (RDF) et Atom.

Le contenu vient d'Internet : on le traite comme non fiable.
- XML lu avec `defusedxml` (refuse entités externes, DTD abusives, « billion laughs »).
- Texte débarrassé de ses balises HTML, raccourci, espaces normalisés.
- Seuls les liens http(s) sont conservés (pas de `javascript:` ni de `data:`).
"""
from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.domain.feeds.models import FeedItem, FeedParseError

SUMMARY_MAX_CHARS = 280
TITLE_MAX_CHARS = 300
_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def clean_text(raw: str | None, limit: int) -> str:
    """Retire les balises HTML, décode les entités, normalise les espaces, raccourcit."""
    text = _CONTROL.sub("", raw or "")
    text = html.unescape(_TAGS.sub(" ", text))
    text = _SPACES.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:.-")
    return f"{cut}…"


def safe_url(raw: str | None) -> str | None:
    value = (raw or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return value


def parse_date(raw: str | None) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    parsed: datetime | None = None
    try:
        parsed = parsedate_to_datetime(value)  # RFC 822 (RSS)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))  # ISO 8601 (Atom, dc:date)
        except ValueError:
            return None
    if parsed is None:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _first_text(item: Element, *names: str) -> str:
    for child in item:
        if _local(child.tag) in names:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def _link(item: Element) -> str | None:
    for child in item:
        if _local(child.tag) != "link":
            continue
        href = child.attrib.get("href")  # Atom
        if href and child.attrib.get("rel", "alternate") == "alternate":
            return safe_url(href)
        if (child.text or "").strip():  # RSS
            return safe_url(child.text)
    guid = _first_text(item, "guid", "id")  # repli : l'identifiant est parfois l'adresse
    return safe_url(guid)


def parse_feed(
    content: bytes, *, source_id: str, source_name: str, tag: str | None = None, limit: int = 30,
) -> list[FeedItem]:
    """Retourne au plus `limit` articles ; lève FeedParseError si le XML est invalide ou dangereux."""
    try:
        root = fromstring(content)
    except (ParseError, DefusedXmlException, ValueError) as exc:
        raise FeedParseError(type(exc).__name__) from exc

    items: list[FeedItem] = []
    seen: set[str] = set()
    for element in root.iter():
        if _local(element.tag) not in ("item", "entry"):
            continue
        title = clean_text(_first_text(element, "title"), TITLE_MAX_CHARS)
        url = _link(element)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        summary = clean_text(
            _first_text(element, "description", "summary", "encoded", "content"), SUMMARY_MAX_CHARS)
        published = parse_date(_first_text(element, "pubDate", "published", "updated", "date"))
        items.append(FeedItem(
            id=hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
            title=title, summary="" if summary == title else summary, url=url,
            published_at=published, source_id=source_id, source_name=source_name, tag=tag))
        if len(items) >= limit:
            break
    return items
