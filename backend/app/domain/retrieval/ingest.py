"""Ingestion des PDF : extraction du texte, découpage en passages, embeddings, stockage."""
from __future__ import annotations

import re
from pathlib import Path

from app.infrastructure.db import vectors
from app.infrastructure.llm import ollama

CHUNK_CHARS, OVERLAP, BATCH = 1500, 200, 16
_SECTION_HEADING = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*[.)]?\s*)?"
    r"(?P<heading>abstract|introduction|background|literature review|related work|"
    r"materials and methods|methods|methodology|statistical analysis|results?|findings|"
    r"discussion|conclusions?|limitations|references)\s*:?\s*$",
    re.IGNORECASE)
_TABLE_CAPTION = re.compile(r"^\s*[\[(]?\s*table\s*(?P<number>\d+|[ivxlcdm]+)\b", re.IGNORECASE)
_TABLE_NARRATIVE = re.compile(
    r"^(?:the\s+(?:study|results|findings|majority|present study|5[- ]point)|"
    r"specifically\b|in contrast\b|on the other hand\b|overall\b|our study\b|"
    r"our results\b|this study\b|these findings\b|table\s+\d+\s+"
    r"(?:shows|illustrates|indicates|demonstrates))",
    re.IGNORECASE)
_ABSTRACT_SUBHEADINGS = {"background", "objective", "methods", "results", "conclusion"}


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Découpe en passages qui se chevauchent un peu (coupe de préférence sur un espace)."""
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)
            end = cut if cut > start else end
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def _section_name(heading: str) -> str:
    normalized = heading.casefold()
    if normalized in {"background", "literature review", "related work"}:
        return "introduction"
    if normalized in {"materials and methods", "methods", "methodology", "statistical analysis"}:
        return "methods"
    if normalized in {"result", "results", "findings"}:
        return "results"
    if normalized in {"conclusion", "conclusions"}:
        return "conclusion"
    return normalized


def _page_blocks(text: str, section: str, table_id: str | None, seen_tables: set[str]
                 ) -> tuple[list[tuple[str, str, str | None, str]], str, str | None]:
    blocks: list[tuple[str, str, str | None, str]] = []
    in_table = table_id is not None
    kind = "table" if in_table else "prose"
    lines: list[str] = []

    def flush() -> None:
        if lines:
            blocks.append((section, kind, table_id, "\n".join(lines)))
            lines.clear()

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        heading = _SECTION_HEADING.fullmatch(line)
        if heading:
            title = heading.group("heading").casefold()
            if section == "abstract" and title in _ABSTRACT_SUBHEADINGS:
                lines.append(line)
                continue
            flush()
            section = _section_name(title)
            kind, table_id, in_table = "prose", None, False
            lines.append(line)
            continue

        caption = _TABLE_CAPTION.match(line)
        if caption:
            caption_id = caption.group("number").casefold()
            continued = bool(re.search(r"\b(?:continued|contd|cont)\b", line, re.IGNORECASE))
            if continued and caption_id in seen_tables:
                if in_table and table_id == caption_id:
                    lines.append(line)
                continue
            flush()
            kind, table_id, in_table = "table", caption_id, True
            seen_tables.add(table_id)
            lines.append(line)
            continue

        if in_table and _TABLE_NARRATIVE.match(line):
            flush()
            kind, table_id, in_table = "prose", None, False
        lines.append(line)

    flush()
    return blocks, section, table_id


def chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    """Split PDF pages at paper sections and table boundaries before size chunking."""
    rows = []
    section, table_id = "body", None
    seen_tables: set[str] = set()
    for page_number, text in pages:
        blocks, section, table_id = _page_blocks(text, section, table_id, seen_tables)
        for block_section, kind, table_id, body in blocks:
            marker = f"[RAG section={block_section} type={kind}"
            if table_id:
                marker += f" table={table_id}"
            marker += "]\n"
            rows.extend(
                {"page": page_number, "content": marker + chunk}
                for chunk in chunk_text(body))
    return rows


def read_pdf(path: Path) -> list[dict]:
    from pypdf import PdfReader

    pages = [
        (number, (page.extract_text() or "").replace("\x00", ""))
        for number, page in enumerate(PdfReader(str(path)).pages, 1)
    ]
    return [{"file_name": path.name, **row} for row in chunk_pages(pages)]


def ingest_folder(folder: Path, reset: bool = False, log=print) -> int:
    pdfs = sorted(folder.rglob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Aucun PDF dans {folder}")
    if reset:
        vectors.reset()
    vectors.ensure_table()
    done = set() if reset else vectors.ingested_files()
    total = 0
    for pdf in pdfs:
        if pdf.name in done:
            log(f"  {pdf.name} : déjà ingéré, ignoré")
            continue
        rows = read_pdf(pdf)
        if not rows:
            log(f"  {pdf.name} : aucun texte (PDF scanné ? un OCR est nécessaire)")
            continue
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            for row, vec in zip(batch, ollama.embed([r["content"] for r in batch])):
                row["embedding"] = vec
            vectors.add_chunks(batch)
        total += len(rows)
        log(f"  {pdf.name} : {len(rows)} passages")
    return total
