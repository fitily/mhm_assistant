from datetime import UTC, datetime

import pytest

from app.domain.feeds.models import FeedParseError
from app.domain.feeds.parser import clean_text, parse_date, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Test</title>
  <item>
    <title>Cholera &amp; floods: response scaled up</title>
    <link>https://example.org/a</link>
    <pubDate>Tue, 24 Nov 2026 09:30:00 GMT</pubDate>
    <description>&lt;p&gt;Teams deployed in &lt;b&gt;three&lt;/b&gt; districts.&amp;nbsp;More soon.&lt;/p&gt;</description>
  </item>
  <item>
    <title>Item without link</title>
  </item>
  <item>
    <title>Dangerous link</title>
    <link>javascript:alert(1)</link>
  </item>
  <item>
    <title>Dated with dc</title>
    <link>https://example.org/b</link>
    <dc:date>2026-11-20T08:00:00Z</dc:date>
  </item>
</channel></rss>""".encode()

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title>
  <entry>
    <title>Atom article</title>
    <link rel="self" href="https://example.org/self"/>
    <link rel="alternate" href="https://example.org/atom-1"/>
    <updated>2026-11-22T10:00:00+03:00</updated>
    <summary type="html">&lt;em&gt;Résumé&lt;/em&gt; court</summary>
  </entry>
</feed>""".encode()

RDF = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <item rdf:about="https://example.org/rdf-1">
    <title>RDF article</title><link>https://example.org/rdf-1</link>
    <dc:date>2026-11-18</dc:date>
  </item>
</rdf:RDF>""".encode()


def parse(content, **kwargs):
    return parse_feed(content, source_id="s", source_name="Source", **kwargs)


def test_rss_items_are_cleaned_and_unsafe_entries_dropped():
    items = parse(RSS)
    assert [i.url for i in items] == ["https://example.org/a", "https://example.org/b"]
    first = items[0]
    assert first.title == "Cholera & floods: response scaled up"
    assert first.summary == "Teams deployed in three districts. More soon."
    assert first.published_at == datetime(2026, 11, 24, 9, 30, tzinfo=UTC)
    assert first.source_id == "s" and first.source_name == "Source"
    assert items[1].published_at == datetime(2026, 11, 20, 8, 0, tzinfo=UTC)


def test_atom_prefers_alternate_link_and_converts_timezone():
    (item,) = parse(ATOM, tag="alerte")
    assert item.url == "https://example.org/atom-1"
    assert item.published_at == datetime(2026, 11, 22, 7, 0, tzinfo=UTC)
    assert item.summary == "Résumé court"
    assert item.tag == "alerte"


def test_rdf_feed_is_supported():
    (item,) = parse(RDF)
    assert item.title == "RDF article"
    assert item.published_at == datetime(2026, 11, 18, tzinfo=UTC)


def test_limit_and_stable_ids():
    many = "<rss><channel>" + "".join(
        f"<item><title>T{n}</title><link>https://example.org/{n}</link></item>" for n in range(10)
    ) + "</channel></rss>"
    items = parse(many.encode(), limit=3)
    assert len(items) == 3
    assert items[0].id == parse(many.encode(), limit=3)[0].id
    assert len({i.id for i in items}) == 3


def test_summary_equal_to_title_is_dropped():
    xml = (b"<rss><channel><item><title>Same</title><link>https://e.org/1</link>"
           b"<description>Same</description></item></channel></rss>")
    assert parse(xml)[0].summary == ""


@pytest.mark.parametrize("payload", [
    b"not xml at all",
    b"<rss><channel><item>",
    b"",
    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
    b"<rss><channel><item><title>&b;</title><link>https://e.org/1</link></item></channel></rss>",
    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b"<rss><channel><item><title>&xxe;</title><link>https://e.org/1</link></item></channel></rss>",
])
def test_invalid_or_dangerous_xml_raises_parse_error(payload):
    with pytest.raises(FeedParseError):
        parse(payload)


def test_clean_text_truncates_on_word_boundary():
    text = clean_text("alpha beta gamma delta epsilon", 18)
    assert text.endswith("…") and len(text) <= 18
    assert text == "alpha beta gamma…"


@pytest.mark.parametrize(("raw", "expected"), [
    ("Tue, 24 Nov 2026 09:30:00 +0300", datetime(2026, 11, 24, 6, 30, tzinfo=UTC)),
    ("2026-11-24T09:30:00Z", datetime(2026, 11, 24, 9, 30, tzinfo=UTC)),
    ("2026-11-24", datetime(2026, 11, 24, tzinfo=UTC)),
    ("yesterday-ish", None),
    ("", None),
    (None, None),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected
