"""Parsers for the public WHO and journal news feeds."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
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
    # « % » est conservé : une URL déjà encodée (%20) ne l'est pas deux fois ; un espace littéral devient %20.
    return urlunsplit(parsed._replace(path=quote(parsed.path, safe="/%:@+,;=-._~!$&'()*"), query=quote(parsed.query, safe="=&%:/?+,;@-._~!$'()*")))


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


# --- Ministère de la Santé Publique de Madagascar (https://www.msanp.gov.mg/index.php/listActualites) ----------------
# Structure observée sur la page : chaque actualité = date (« 20 nov. 2026 »), titre en MAJUSCULES, image de couverture
# (/upload/Article/Cover/…), extrait tronqué, lien « Voir Plus » vers /index.php/article?id=N.
# Le HTML exact n'est pas figé : on retrouve chaque carte par son lien article?id=N (plus grand bloc ne contenant qu'un
# seul identifiant), puis on y cherche titre, date, image et extrait. À vérifier sur le vrai HTML : scripts/check_news.py.
_MSANP_BASE = "https://www.msanp.gov.mg/index.php/listActualites"
_MSANP_HOST = ".msanp.gov.mg"
_ARTICLE_ID = re.compile(r"article\?id=(\d+)")
_MORE_LINK = re.compile(r"^(voir\s+plus|lire\s+la\s+suite|read\s+more|hijery\s+bebe\s+kokoa|\.\.\.)\W*$", re.IGNORECASE)
_MONTHS = {
    **{name: i for i, names in enumerate((
        ("janv", "janvier", "janoary"), ("fevr", "fevrier", "febroary", "feb"), ("mars", "martsa"),
        ("avr", "avril", "aprily"), ("mai", "mey"), ("juin", "jona"), ("juil", "juillet", "jolay"),
        ("aout", "aogositra"), ("sept", "septembre", "septambra"), ("oct", "octobre", "oktobra"),
        ("nov", "novembre", "novambra"), ("dec", "decembre", "desambra")), 1) for name in names},
}
_FR_DATE = re.compile(r"\b(\d{1,2})\s+([^\W\d_]+)\.?\s+(\d{4})\b")


def _ascii(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()


def _french_date(text: str) -> str | None:
    """« 20 nov. 2026 » -> « 2026-11-20T00:00:00+00:00 » (date seule : minuit UTC, comme les pages de l'OMS)."""
    for day, month_name, year in _FR_DATE.findall(text):
        month = _MONTHS.get(_ascii(month_name).rstrip("."))
        if month:
            try:
                return datetime(int(year), month, int(day), tzinfo=timezone.utc).isoformat()
            except ValueError:
                continue
    return None


def _article_ids(node: _Node) -> set[str]:
    return {m.group(1) for n in node.descendants() if n.tag == "a" and (m := _ARTICLE_ID.search(n.attrs.get("href", "")))}


def _cards(node: _Node) -> list[_Node]:
    """Plus grands blocs ne contenant les liens que d'UNE seule actualité."""
    ids = _article_ids(node)
    if not ids:
        return []
    if len(ids) == 1:
        return [node]
    return [card for child in node.children if isinstance(child, _Node) for card in _cards(child)]


def _sentence_case(title: str) -> str:
    """Les titres du site sont tout en majuscules, difficiles à lire : « AGORA SANTÉ… » -> « Agora santé… »."""
    letters = [c for c in title if c.isalpha()]
    if len(letters) > 12 and all(c.isupper() for c in letters):
        lowered = title.lower()
        return re.sub(r"(^|[.:!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), lowered)
    return title


def parse_msanp_news(html: str) -> list[dict]:
    parser = _TreeParser()
    parser.feed(html)
    articles: dict[str, dict] = {}
    for card in _cards(parser.root):
        link = next((n for n in _elements(card, "a") if _ARTICLE_ID.search(n.attrs.get("href", ""))), None)
        if link is None:
            continue
        url = _safe_url(link.attrs["href"], _MSANP_BASE, _MSANP_HOST)
        if not url:
            continue
        heading = next((n for n in _elements(card) if n.tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and _text(n)), None)
        title = _text(heading) if heading else ""
        if not title:  # pas de titre balisé : le texte de lien le plus long qui n'est pas « Voir Plus »
            link_texts = [_text(n) for n in _elements(card, "a") if _text(n) and not _MORE_LINK.match(_text(n))]
            title = max(link_texts, key=len, default="")
        title = _sentence_case(re.sub(r"\s+", " ", title).strip())
        if not title:
            continue
        card_text = _text(card)
        published_at = _french_date(card_text)
        summary_candidates = [
            _text(n) for n in _elements(card)
            if n.tag in {"p", "div", "span"} and not any(isinstance(c, _Node) and c.tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"} for c in n.children)
        ]
        raw_title = _text(heading) if heading else title
        summary = max(
            (t for t in summary_candidates
             if t and t.casefold() != raw_title.casefold() and t.casefold() != title.casefold()
             and not _MORE_LINK.match(t) and not (_FR_DATE.fullmatch(t.strip()))),
            key=len, default="",
        )
        image_node = next((n for n in _elements(card, "img") if n.attrs.get("src") or n.attrs.get("data-src")), None)
        image = (_safe_url(image_node.attrs.get("src") or image_node.attrs.get("data-src", ""), _MSANP_BASE, _MSANP_HOST)
                 if image_node else None)
        articles.setdefault(url, _article(
            title=title, url=url, summary=summary, source="Ministère de la Santé Publique",
            published_at=published_at, category="breaking", image=image,
        ))
    return list(articles.values())
