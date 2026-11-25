from fastapi.testclient import TestClient

from app.api.deps import current_user
from app.domain.feeds.models import FeedFetchError, FeedSource
from app.main import create_app
from app.services.feed_service import FeedAggregator, get_aggregator

PAGE = (b"<rss><channel><item><title>Outbreak update</title><link>https://e.org/1</link>"
        b"<pubDate>Wed, 25 Nov 2026 08:00:00 GMT</pubDate><description>Short</description>"
        b"</item></channel></rss>")


def client_with(aggregator):
    app = create_app()
    app.dependency_overrides[current_user] = lambda: "test"
    app.dependency_overrides[get_aggregator] = lambda: aggregator
    return TestClient(app)


def aggregator(fetch):
    sources = (
        FeedSource("who", "OMS", "news", ("https://who/feed",)),
        FeedSource("afro", "OMS Afrique", "news", ("https://afro/feed",), tag="alerte"),
        FeedSource("nejm", "NEJM", "research", ("https://nejm/feed",)),
    )
    return FeedAggregator(sources=sources, fetch=fetch, fetch_pubmed=lambda *a, **k: [])


def test_breaking_news_returns_items_and_per_source_status():
    def fetch(url, *, timeout):
        if "afro" in url:
            raise FeedFetchError("HTTP 500")
        return PAGE

    response = client_with(aggregator(fetch)).get("/v1/feeds/breaking-news")
    body = response.json()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, max-age=60"
    assert body["items"][0]["title"] == "Outbreak update"
    assert body["items"][0]["source_name"] == "OMS"
    assert body["items"][0]["published_at"].startswith("2026-11-25T08:00:00")
    assert {s["id"]: s["status"] for s in body["sources"]} == {"who": "ok", "afro": "error"}
    assert "generated_at" in body


def test_research_only_returns_research_sources():
    response = client_with(aggregator(lambda url, *, timeout: PAGE)).get("/v1/feeds/research")
    body = response.json()
    assert [s["id"] for s in body["sources"]] == ["nejm"]
    assert {i["source_id"] for i in body["items"]} == {"nejm"}


def test_refresh_flag_is_accepted():
    calls = []

    def fetch(url, *, timeout):
        calls.append(url)
        return PAGE

    http = client_with(aggregator(fetch))
    http.get("/v1/feeds/breaking-news")
    assert http.get("/v1/feeds/breaking-news?refresh=true").status_code == 200
    assert len(calls) == 2  # le rafraîchissement forcé est limité à 1 fois / 30 s


def test_feeds_require_authentication(monkeypatch):
    from app.core import config

    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", "secret")
    config.get_settings.cache_clear()
    try:
        app = create_app()
        app.dependency_overrides[get_aggregator] = lambda: aggregator(lambda url, *, timeout: PAGE)
        response = TestClient(app).get("/v1/feeds/breaking-news")
        assert response.status_code == 401
    finally:
        config.get_settings.cache_clear()
