"""Parsers for the public WHO and journal news feeds."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree


@dataclass(slots=True)
class _Node:
    tag: str
    attrs: dict[str, str]
    children: list[_Node | str] = field(default_factory=list)

    def descendants(self):
        for child in self.children:
            if isinstance(child, _Node):
                yield child
                yield from child.descendants()

    def text(self) -> str:
        return " ".join(
            part for child in self.children
            for part in ([child] if isinstance(child, str) else [child.text()])
            if part
        )


class _TreeParser(HTMLParser):
    _VOID_TAGS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    })

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in self._VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(_Node(tag, {key: value or "" for key, value in attrs}))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].children.append(data)


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _elements(node: _Node, tag: str | None = None):
    return (child for child in node.descendants() if tag is None or child.tag == tag)


def _has_class(node: _Node, class_name: str) -> bool:
    return class_name in node.attrs.get("class", "").split()


def _text(node: _Node) -> str:
    return re.sub(r"\s+", " ", node.text()).strip()


def _date(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            parsed = None
            for date_format in ("%Y-%m-%d-%H:%M", "%d %B %Y"):
                try:
                    parsed = datetime.strptime(value, date_format)
                    break
                except ValueError:
                    continue
            if parsed is None:
                match = re.search(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b", value)
                if not match:
                    return None
                try:
                    parsed = datetime.strptime(match.group(), "%d %B %Y")
                except ValueError:
                    return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _safe_url(value: str, base: str, allowed_host: str) -> str | None:
    url = urljoin(base, value.strip())
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not (parsed.hostname or "").casefold().endswith(allowed_host):
        return None
    return url


def _plain_html(value: str) -> str:
    parser = _PlainTextParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _article(
    *,
    title: str,
    url: str,
    summary: str,
    source: str,
    published_at: str | None,
    category: str,
    image: str | None = None,
) -> dict:
    return {
        "id": url,
        "title": title,
        "summary": summary[:360].rstrip() + ("…" if len(summary) > 360 else ""),
        "source": source,
        "url": url,
        "published_at": published_at,
        "category": category,
        "image": image,
    }


def parse_who_news(html: str) -> list[dict]:
    parser = _TreeParser()
    parser.feed(html)
    articles = []
    for card in _elements(parser.root, "div"):
        if not _has_class(card, "list-view--item"):
            continue
        link = next(
            (
                node for node in _elements(card, "a")
                if "/news/item/" in node.attrs.get("href", "")
            ),
            None,
        )
        if link is None:
            continue
        url = _safe_url(link.attrs.get("href", ""), "https://www.who.int/news", ".who.int")
        heading = next((node for node in _elements(card) if _has_class(node, "heading")), None)
        title = _text(heading) if heading else link.attrs.get("aria-label", "").strip()
        if not url or not title:
            continue
        type_node = next(
            (node for node in _elements(card) if _has_class(node, "sf-tags-list-item")),
            None,
        )
        if type_node and _text(type_node).casefold() == "employment":
            continue
        date_node = next((node for node in _elements(card) if _has_class(node, "timestamp")), None)
        summary_node = next(
            (
                node for node in _elements(card)
                if any(_has_class(node, name) for name in ("summary", "description", "abstract"))
            ),
            None,
        )
        image_node = next(
            (node for node in _elements(card) if node.attrs.get("data-image")),
            None,
        )
        if image_node is None:
            image_node = next((node for node in _elements(card, "img") if node.attrs.get("src")), None)
        image = None
        if image_node:
            image = _safe_url(
                image_node.attrs.get("data-image") or image_node.attrs.get("src", ""),
                "https://www.who.int/news",
                ".who.int",
            )
        articles.append(
            _article(
                title=title,
                url=url,
                summary=_text(summary_node) if summary_node else "",
                source="WHO",
                published_at=_date(_text(date_node)) if date_node else None,
                category="update",
                image=image,
            )
        )
    return articles


def parse_who_afro_updates(html: str) -> list[dict]:
    parser = _TreeParser()
    parser.feed(html)
    articles = []
    for card in _elements(parser.root, "article"):
        link = next(
            (
                node for node in _elements(card, "a")
                if "/news/" in urlsplit(node.attrs.get("href", "")).path
            ),
            None,
        )
        if link is None:
            continue
        url = _safe_url(link.attrs.get("href", ""), "https://www.afro.who.int", ".who.int")
        heading = next((node for node in _elements(card) if node.tag in {"h2", "h3"}), None)
        title = _text(heading) if heading else link.attrs.get("aria-label", "").strip()
        if not url or not title:
            continue
        date_node = next(
            (node for node in _elements(card) if node.tag == "time" and node.attrs.get("datetime")),
            None,
        )
        date_value = date_node.attrs["datetime"] if date_node else _text(card)
        summary_node = next(
            (node for node in _elements(card, "p") if _text(node) and _text(node) != title),
            None,
        )
        image_node = next((node for node in _elements(card, "img") if node.attrs.get("src")), None)
        image = (
            _safe_url(image_node.attrs["src"], "https://www.afro.who.int", ".who.int")
            if image_node else None
        )
        articles.append(
            _article(
                title=title,
                url=url,
                summary=_text(summary_node) if summary_node else "",
                source="WHO Africa",
                published_at=_date(date_value),
                category="breaking",
                image=image,
            )
        )
    return articles


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ElementTree.Element, names: set[str]) -> str:
    for child in node:
        if _local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def parse_journal_feed(xml: str, *, source: str, host: str) -> list[dict]:
    root = ElementTree.fromstring(xml)
    fallback_date = next(
        (
            child.text.strip()
            for node in root.iter()
            if _local_name(node.tag) == "channel"
            for child in node
            if _local_name(child.tag) == "publicationdate" and child.text
        ),
        "",
    )
    articles = []
    for item in (node for node in root.iter() if _local_name(node.tag) == "item"):
        title = _child_text(item, {"title"})
        link = _child_text(item, {"link"}) or next(
            (value for key, value in item.attrib.items() if _local_name(key) == "about"),
            "",
        )
        url = _safe_url(link, f"https://{host}", f".{host}")
        if not title or not url:
            continue
        summary = ""
        date_value = ""
        for node in item.iter():
            name = _local_name(node.tag)
            if not summary and name in {"description", "encoded", "summary", "abstract"} and node.text:
                summary = _plain_html(node.text)
            if not date_value and name in {
                "date", "issued", "published", "pubdate", "publicationdate",
                "coverdate", "dateissued",
            } and node.text:
                date_value = node.text.strip()
        articles.append(
            _article(
                title=title,
                url=url,
                summary=summary,
                source=source,
                published_at=_date(date_value or fallback_date),
                category="research",
            )
        )
    articles.sort(key=lambda article: article["published_at"] or "", reverse=True)
    return articles
