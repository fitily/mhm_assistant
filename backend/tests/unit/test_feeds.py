"""Parsing and access-control tests for the medical news feed."""
from __future__ import annotations

import asyncio
import datetime as dt

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import get_settings
from app.main import create_app
from app.services import auth_service, feed_service
from app.domain.feeds.parser import parse_journal_feed, parse_who_afro_updates, parse_who_news


def test_who_news_parser_extracts_article_metadata_and_skips_employment():
    html = """
    <div class="list-view--item">
      <a href="/news/item/24-11-2026-example" aria-label="WHO health announcement">
        <div class="date"><span class="timestamp">24 November 2026</span>
          <div class="sf-tags-list-item">News release</div></div>
        <p class="heading">WHO health announcement</p>
        <div class="background-image" data-image="https://cdn.who.int/health.jpg"></div>
      </a>
    </div>
    <div class="list-view--item">
      <a href="/news/item/24-11-2026-jobs"><div class="sf-tags-list-item">Employment</div>
        <p class="heading">Call for consultant</p></a>
    </div>
    """

    articles = parse_who_news(html)

    assert len(articles) == 1
    assert articles[0]["title"] == "WHO health announcement"
    assert articles[0]["source"] == "WHO"
    assert articles[0]["category"] == "update"
    assert articles[0]["published_at"] == "2026-11-24T00:00:00+00:00"
    assert articles[0]["image"] == "https://cdn.who.int/health.jpg"


def test_who_africa_parser_keeps_emergency_news_and_skips_other_articles():
    html = """
    <main>
      <article>
        <a href="/countries/kenya/news/health-update">
          <span>20 November 2026 | News Release</span>
          <h3>Regional health update</h3>
        </a>
        <p>New regional response measures.</p>
      </article>
      <article><a href="/countries/kenya/multimedia/video"><h3>Video</h3></a></article>
    </main>
    """

    articles = parse_who_afro_updates(html)

    assert len(articles) == 1
    assert articles[0]["title"] == "Regional health update"
    assert articles[0]["source"] == "WHO Africa"
    assert articles[0]["category"] == "breaking"
    assert articles[0]["published_at"] == "2026-11-20T00:00:00+00:00"
    assert articles[0]["summary"] == "New regional response measures."


@pytest.mark.parametrize(
    ("source", "host", "xml", "expected_title", "expected_date"),
    [
        (
            "The Lancet",
            "thelancet.com",
            """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                 xmlns="http://purl.org/rss/1.0/" xmlns:prism="http://prismstandard.org/namespaces/1.2/basic/">
              <channel><prism:publicationDate>2026-11-24-08:00</prism:publicationDate></channel>
              <item rdf:about="https://www.thelancet.com/journals/lancet/article/example">
                <title>New study</title><link>https://www.thelancet.com/journals/lancet/article/example</link>
                <description>&lt;p&gt;Study summary.&lt;/p&gt;</description>
              </item>
            </rdf:RDF>""",
            "New study",
            "2026-11-24T08:00:00+00:00",
        ),
        (
            "NEJM",
            "nejm.org",
            """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                 xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
              <item rdf:about="https://www.nejm.org/doi/full/example">
                <title>Clinical trial</title><link>https://www.nejm.org/doi/full/example</link>
                <description>Trial overview.</description><dc:date>2026-11-23T10:00:00Z</dc:date>
              </item>
            </rdf:RDF>""",
            "Clinical trial",
            "2026-11-23T10:00:00+00:00",
        ),
    ],
)
def test_journal_parser_extracts_research_publications(source, host, xml, expected_title, expected_date):
    articles = parse_journal_feed(xml, source=source, host=host)

    assert len(articles) == 1
    assert articles[0]["title"] == expected_title
    assert articles[0]["source"] == source
    assert articles[0]["category"] == "research"
    assert articles[0]["published_at"] == expected_date
    assert articles[0]["summary"]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", "s" * 48)
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    auth_service.throttle.clear()
    yield TestClient(create_app())
    get_settings.cache_clear()
    auth_service.throttle.clear()


def _auth(role):
    token, _ = security.create_access_token(subject=f"{role}@mhm.org", role=role, name="Test")
    return {"Authorization": f"Bearer {token}"}


def test_news_endpoint_is_doctor_only(client, monkeypatch):
    async def news():
        return {
            "items": [],
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "connected": True,
            "sources": [{
                "key": "who",
                "label": "WHO",
                "url": "https://www.who.int/news",
                "connected": True,
            }],
        }

    monkeypatch.setattr(feed_service, "get_news", news)

    response = client.get("/v1/news", headers=_auth("doctor"))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["sources"][0]["label"] == "WHO"
    assert client.get("/v1/news", headers=_auth("admin")).status_code == 403
    assert client.get("/v1/news").status_code == 401


def test_news_endpoint_reports_when_all_sources_are_unavailable(client, monkeypatch):
    async def unavailable():
        raise feed_service.FeedsUnavailableError

    monkeypatch.setattr(feed_service, "get_news", unavailable)

    response = client.get("/v1/news", headers=_auth("doctor"))

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_feed_service_returns_available_sources_when_one_source_fails(monkeypatch):
    async def fetch_source(client, *, key, label, url, parse):
        if key == "who":
            raise httpx.ConnectError("source unavailable")
        return (
            {"key": key, "label": label, "url": url, "connected": True},
            [{
                "id": url,
                "url": url,
                "title": f"Latest from {label}",
                "published_at": "2026-11-24T00:00:00+00:00",
            }],
        )

    monkeypatch.setattr(feed_service, "_fetch_source", fetch_source)
    feed_service.clear_cache()
    try:
        payload = asyncio.run(feed_service._fetch_all())
    finally:
        feed_service.clear_cache()

    assert payload["connected"] is False
    assert len(payload["items"]) == 3
    assert [source["connected"] for source in payload["sources"]] == [False, True, True, True]


# --- période : 7 derniers jours, d'après la date de PUBLICATION ---------------------------------------------------

NOW = dt.datetime(2026, 11, 26, 5, 30, tzinfo=dt.timezone.utc)   # 26/11/2026 08:30 à Madagascar (UTC+3)


def _article(published_at, **extra):
    return {"id": str(published_at), "url": f"https://x/{published_at}", "title": "T", "summary": "", "source": "WHO",
            "category": "update", "published_at": published_at, **extra}


def _window(monkeypatch, items, now=NOW, **kw):
    monkeypatch.setenv("APP_TZ", "Indian/Antananarivo")
    get_settings.cache_clear()
    try:
        payload = {"items": items, "updated_at": "x", "connected": True, "sources": []}
        return feed_service.filter_news(payload, category=kw.get("category", "all"), query=kw.get("query", ""), now=now)
    finally:
        get_settings.cache_clear()


def test_window_starts_at_local_midnight_seven_days_ago(monkeypatch):
    out = _window(monkeypatch, [
        _article("2026-11-18T20:59:00+00:00"),   # 18/11 23:59 à Madagascar : trop ancien
        _article("2026-11-18T21:00:00+00:00"),   # 19/11 00:00 à Madagascar : premier instant gardé
        _article("2026-11-19T00:00:00+00:00"),   # date seule « 19 Nov » (minuit UTC) : gardé toute la journée du 26
        _article("2026-11-26T05:00:00+00:00"),
    ])
    assert [i["published_at"] for i in out["items"]] == [
        "2026-11-18T21:00:00+00:00", "2026-11-19T00:00:00+00:00", "2026-11-26T05:00:00+00:00"]
    assert out["window_days"] == 7 and out["since"] == "2026-11-18T21:00:00+00:00"


def test_window_follows_the_consultation_date(monkeypatch):
    items = [_article("2026-11-19T10:00:00+00:00"), _article("2026-11-25T10:00:00+00:00")]
    assert len(_window(monkeypatch, items, now=NOW)["items"]) == 2
    later = NOW + dt.timedelta(days=3)               # le 29/11 : le 19/11 sort de la période, sans rien recharger
    assert [i["published_at"] for i in _window(monkeypatch, items, now=later)["items"]] == ["2026-11-25T10:00:00+00:00"]


def test_articles_without_a_usable_date_or_from_the_future_are_excluded(monkeypatch):
    out = _window(monkeypatch, [
        _article(None), _article(""), _article("pas une date"),
        _article("2026-11-26T05:40:00+00:00"),   # +10 min : décalage d'horloge toléré
        _article("2026-11-26T06:00:00+00:00"),   # +30 min : pas encore publié
        _article("2026-12-03T00:00:00+00:00"),   # numéro de revue daté dans le futur
        _article("2026-11-25T10:00:00"),         # sans fuseau : lu comme UTC
    ])
    assert [i["published_at"] for i in out["items"]] == ["2026-11-26T05:40:00+00:00", "2026-11-25T10:00:00"]


def test_window_combines_with_category_and_search(monkeypatch):
    items = [_article("2026-11-25T10:00:00+00:00", category="research", title="Malaria trial"),
             _article("2026-11-25T11:00:00+00:00", category="update", title="Malaria alert"),
             _article("2026-10-01T11:00:00+00:00", category="research", title="Malaria old")]
    out = _window(monkeypatch, items, category="research", query="malaria")
    assert [i["title"] for i in out["items"]] == ["Malaria trial"]


def test_endpoint_returns_only_recent_articles_with_the_window(client, monkeypatch):
    now = dt.datetime.now(dt.timezone.utc)

    async def news():
        return {"items": [_article((now - dt.timedelta(days=1)).isoformat(), title="Recent"),
                          _article((now - dt.timedelta(days=30)).isoformat(), title="Old")],
                "updated_at": now.isoformat(), "connected": True, "sources": []}

    monkeypatch.setattr(feed_service, "get_news", news)
    body = client.get("/v1/news", headers=_auth("doctor")).json()
    assert [a["title"] for a in body["items"]] == ["Recent"]
    assert body["window_days"] == 7 and body["since"]
