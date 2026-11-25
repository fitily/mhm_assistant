"""Secours pour les revues : PubMed (API publique NCBI E-utilities) quand les flux RSS d'une revue
sont bloqués ou absents. Les liens pointent vers le DOI, donc vers le site de la revue."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import httpx

from app.domain.feeds.models import FeedFetchError, FeedItem
from app.domain.feeds.parser import clean_text
from app.infrastructure.feeds.client import USER_AGENT

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _get_json(
    client: httpx.Client, path: str, params: dict[str, str | int],
) -> dict:
    try:
        response = client.get(f"{EUTILS}/{path}", params={**params, "retmode": "json"})
        if response.status_code != 200:
            raise FeedFetchError(f"HTTP {response.status_code}")
        return json.loads(response.content)
    except (httpx.HTTPError, ValueError) as exc:
        raise FeedFetchError(type(exc).__name__) from exc


def _published(record: dict) -> datetime | None:
    raw = str(record.get("sortpubdate") or record.get("epubdate") or "").strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d", "%Y %b %d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _doi(record: dict) -> str | None:
    for article_id in record.get("articleids") or []:
        if article_id.get("idtype") == "doi" and article_id.get("value"):
            return str(article_id["value"]).strip()
    return None


def latest(
    term: str, *, source_id: str, source_name: str, limit: int, timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> list[FeedItem]:
    with httpx.Client(timeout=timeout, transport=transport,
                      headers={"User-Agent": USER_AGENT}) as client:
        found = _get_json(client, "esearch.fcgi", {
            "db": "pubmed", "term": term, "sort": "pub_date", "retmax": limit})
        ids = [str(i) for i in (found.get("esearchresult") or {}).get("idlist", [])]
        if not ids:
            return []
        summary = _get_json(client, "esummary.fcgi", {"db": "pubmed", "id": ",".join(ids)})

    items: list[FeedItem] = []
    result = summary.get("result") or {}
    for uid in ids:
        record = result.get(uid)
        if not isinstance(record, dict):
            continue
        title = clean_text(record.get("title"), 300)
        if not title:
            continue
        doi = _doi(record)
        url = f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        names = [a.get("name", "") for a in record.get("authors") or [] if a.get("name")]
        authors = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
        items.append(FeedItem(
            id=hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
            title=title, summary=clean_text(authors, 280), url=url, published_at=_published(record),
            source_id=source_id, source_name=source_name))
    return items
