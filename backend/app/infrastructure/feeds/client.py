"""Téléchargement des flux : délais courts, taille plafonnée, aucune donnée de l'application envoyée."""
from __future__ import annotations

import httpx

from app.domain.feeds.models import FeedFetchError

MAX_BYTES = 2_000_000
USER_AGENT = "MHM-Assistant/0.1 (health news reader for physicians)"  # en-tête HTTP : ASCII uniquement
ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"


def fetch_bytes(
    url: str, *, timeout: float, max_bytes: int = MAX_BYTES,
    transport: httpx.BaseTransport | None = None,
) -> bytes:
    """GET `url` et retourne le corps. Lève FeedFetchError (message sans détail interne)."""
    try:
        with httpx.Client(
            timeout=timeout, follow_redirects=True, transport=transport,
            headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
        ) as client, client.stream("GET", url) as response:
            if response.status_code != 200:
                raise FeedFetchError(f"HTTP {response.status_code}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise FeedFetchError("réponse trop volumineuse")
            return bytes(body)
    except httpx.HTTPError as exc:
        raise FeedFetchError(type(exc).__name__) from exc
