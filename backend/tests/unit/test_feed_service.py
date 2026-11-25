import json
from datetime import UTC, datetime

import httpx
import pytest

from app.domain.feeds.models import FeedFetchError, FeedItem, FeedSource
from app.infrastructure.feeds import client, pubmed
from app.services.feed_service import FeedAggregator


def rss(*entries):
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate></item>"
        for t, u, d in entries)
    return f"<rss><channel>{body}</channel></rss>".encode()


NEWS_A = rss(("Older", "https://e.org/old", "Mon, 23 Nov 2026 08:00:00 GMT"),
             ("Newest", "https://e.org/new", "Wed, 25 Nov 2026 08:00:00 GMT"))
NEWS_B = rss(("Middle", "https://e.org/mid", "Tue, 24 Nov 2026 08:00:00 GMT"),
             ("Newest again", "https://e.org/new", "Wed, 25 Nov 2026 08:00:00 GMT"))


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Fetcher:
    def __init__(self, pages):
        self.pages = dict(pages)
        self.calls = []

    def __call__(self, url, *, timeout):
        self.calls.append(url)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return page


def make(pages, sources=None, pubmed_items=None, clock=None):
    fetcher = Fetcher(pages)
    pubmed_calls = []

    def fake_pubmed(term, **kwargs):
        pubmed_calls.append(term)
        if isinstance(pubmed_items, Exception):
            raise pubmed_items
        return pubmed_items or []

    sources = sources or (
        FeedSource("a", "Source A", "news", ("https://a/feed",)),
        FeedSource("b", "Source B", "news", ("https://b/feed",), tag="alerte"),
        FeedSource("j", "Journal", "research", ("https://j/feed",), pubmed_term="journal[ta]"),
    )
    agg = FeedAggregator(sources=sources, fetch=fetcher, fetch_pubmed=fake_pubmed,
                         clock=clock or Clock())
    return agg, fetcher, pubmed_calls


def test_group_is_merged_sorted_and_deduplicated():
    agg, _, _ = make({"https://a/feed": NEWS_A, "https://b/feed": NEWS_B})
    bundle = agg.get_group("news")
    assert [i.title for i in bundle.items] == ["Newest", "Middle", "Older"]
    assert [(s.id, s.status, s.count) for s in bundle.sources] == [("a", "ok", 2), ("b", "ok", 2)]
    assert {i.tag for i in bundle.items if i.source_id == "b"} == {"alerte"}


def test_results_are_cached_until_ttl_expires():
    clock = Clock()
    agg, fetcher, _ = make({"https://a/feed": NEWS_A, "https://b/feed": NEWS_B}, clock=clock)
    agg.get_group("news")
    agg.get_group("news")
    assert len(fetcher.calls) == 2  # une fois par source, pas une fois par appel
    clock.now += 1801
    agg.get_group("news")
    assert len(fetcher.calls) == 4


def test_forced_refresh_is_rate_limited():
    clock = Clock()
    agg, fetcher, _ = make({"https://a/feed": NEWS_A, "https://b/feed": NEWS_B}, clock=clock)
    agg.get_group("news")
    clock.now += 10
    agg.get_group("news", refresh=True)
    assert len(fetcher.calls) == 2
    clock.now += 25
    agg.get_group("news", refresh=True)
    assert len(fetcher.calls) == 4


def test_failed_source_keeps_last_known_items_as_stale():
    clock = Clock()
    agg, fetcher, _ = make({"https://a/feed": NEWS_A, "https://b/feed": NEWS_B}, clock=clock)
    agg.get_group("news")
    fetcher.pages["https://a/feed"] = FeedFetchError("HTTP 503")
    clock.now += 1801
    bundle = agg.get_group("news")
    status = {s.id: s for s in bundle.sources}
    assert status["a"].status == "stale" and status["a"].count == 2
    assert status["b"].status == "ok"
    assert "Older" in [i.title for i in bundle.items]


def test_failed_source_without_history_reports_error_without_raising():
    agg, _, _ = make({"https://a/feed": FeedFetchError("HTTP 403"),
                      "https://b/feed": b"<html>blocked</html>"})
    bundle = agg.get_group("news")
    assert bundle.items == []
    assert [s.status for s in bundle.sources] == ["error", "error"]


def test_failed_source_is_retried_only_after_a_minute():
    clock = Clock()
    agg, fetcher, _ = make({"https://a/feed": FeedFetchError("x"),
                            "https://b/feed": FeedFetchError("x")}, clock=clock)
    agg.get_group("news")
    clock.now += 30
    agg.get_group("news")
    assert len(fetcher.calls) == 2
    clock.now += 31
    agg.get_group("news")
    assert len(fetcher.calls) == 4


def test_pubmed_fallback_when_journal_feed_is_blocked():
    paper = FeedItem("1", "Trial result", "Doe J", "https://doi.org/10.1/x",
                     datetime(2026, 11, 20, tzinfo=UTC), "j", "Journal")
    agg, _, calls = make({"https://j/feed": FeedFetchError("HTTP 403")}, pubmed_items=[paper])
    bundle = agg.get_group("research")
    assert calls == ["journal[ta]"]
    assert bundle.sources[0].via == "pubmed" and bundle.sources[0].status == "ok"
    assert bundle.items == [paper]


def test_pubmed_not_used_when_rss_works():
    agg, _, calls = make({"https://j/feed": NEWS_A})
    bundle = agg.get_group("research")
    assert calls == [] and bundle.sources[0].via == "rss"


def test_both_rss_and_pubmed_down_is_an_error_status():
    agg, _, _ = make({"https://j/feed": FeedFetchError("x")}, pubmed_items=FeedFetchError("y"))
    bundle = agg.get_group("research")
    assert bundle.sources[0].status == "error" and bundle.items == []


def test_unknown_group_is_empty():
    agg, _, _ = make({})
    assert agg.get_group("nope").items == []


# --- client HTTP ---------------------------------------------------------------------------
def test_fetch_bytes_returns_body_and_sends_identifying_user_agent():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, content=b"<rss/>")

    body = client.fetch_bytes("https://e.org/f", timeout=3, transport=httpx.MockTransport(handler))
    assert body == b"<rss/>" and seen["ua"].startswith("MHM-Assistant")


@pytest.mark.parametrize("status", [403, 404, 500])
def test_fetch_bytes_rejects_non_200(status):
    transport = httpx.MockTransport(lambda r: httpx.Response(status))
    with pytest.raises(FeedFetchError, match=str(status)):
        client.fetch_bytes("https://e.org/f", timeout=3, transport=transport)


def test_fetch_bytes_rejects_oversized_response():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 5000))
    with pytest.raises(FeedFetchError, match="volumineuse"):
        client.fetch_bytes("https://e.org/f", timeout=3, max_bytes=1000, transport=transport)


def test_fetch_bytes_wraps_network_errors():
    def boom(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(FeedFetchError):
        client.fetch_bytes("https://e.org/f", timeout=3, transport=httpx.MockTransport(boom))


# --- PubMed --------------------------------------------------------------------------------
def pubmed_transport():
    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            assert request.url.params["term"] == '"N Engl J Med"[ta]'
            return httpx.Response(200, content=json.dumps(
                {"esearchresult": {"idlist": ["111", "222", "333"]}}).encode())
        return httpx.Response(200, content=json.dumps({"result": {
            "uids": ["111", "222"],
            "111": {"title": "Ravulizumab in <i>IgA</i> Nephropathy.", "sortpubdate": "2026/11/12 00:00",
                    "authors": [{"name": "A B"}, {"name": "C D"}, {"name": "E F"}, {"name": "G H"}],
                    "articleids": [{"idtype": "pubmed", "value": "111"},
                                   {"idtype": "doi", "value": "10.1056/NEJMoa1"}]},
            "222": {"title": "No DOI paper", "sortpubdate": "2026/11/10 00:00", "authors": []},
        }}).encode())
    return httpx.MockTransport(handler)


def test_pubmed_latest_builds_doi_links_and_skips_missing_records():
    items = pubmed.latest('"N Engl J Med"[ta]', source_id="nejm", source_name="NEJM",
                          limit=15, timeout=3, transport=pubmed_transport())
    assert [i.title for i in items] == ["Ravulizumab in IgA Nephropathy.", "No DOI paper"]
    assert items[0].url == "https://doi.org/10.1056/NEJMoa1"
    assert items[0].summary == "A B, C D, E F et al."
    assert items[0].published_at == datetime(2026, 11, 12, tzinfo=UTC)
    assert items[1].url == "https://pubmed.ncbi.nlm.nih.gov/222/"


def test_pubmed_http_error_is_a_fetch_error():
    transport = httpx.MockTransport(lambda r: httpx.Response(429))
    with pytest.raises(FeedFetchError):
        pubmed.latest("x", source_id="s", source_name="S", limit=5, timeout=3, transport=transport)
