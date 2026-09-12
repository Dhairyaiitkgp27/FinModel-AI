"""Section-aware text chunking.

Splits a filing's page text into overlapping :class:`DocumentChunk` spans, each
tagged with its page number and the section heading it falls under (e.g.
``Item 1A. Risk Factors``). Clean page/section attribution is what lets answers
carry precise citations.

Chunking is per page (so each chunk has a single page number) and per section
within a page; the active section carries across pages until a new heading
appears. Chunks are character-windowed with overlap, breaking on whitespace so
words are not split mid-token.
"""
from __future__ import annotations

import re

from ..models.rag import DocumentChunk

# Headings we recognise in SEC-style filings.
_HEADING_PATTERNS = [
    re.compile(r"^\s*(item\s+\d+[a-z]?\.?.*)$", re.IGNORECASE),
    re.compile(r"^\s*(part\s+[ivx]+\b.*)$", re.IGNORECASE),
]


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    # Explicit SEC item/part headings (may be long, e.g. a full MD&A title).
    if any(p.match(stripped) for p in _HEADING_PATTERNS):
        return True
    # An all-caps, punctuation-light short line is treated as a section heading.
    letters = [c for c in stripped if c.isalpha()]
    return len(stripped) <= 60 and bool(letters) and stripped == stripped.upper()


def _split_into_sections(text: str, current: str | None) -> list[tuple[str | None, str]]:
    """Split page text into ``(section, body)`` segments by heading lines."""
    segments: list[tuple[str | None, str]] = []
    buffer: list[str] = []
    section = current

    for line in text.splitlines():
        if _is_heading(line):
            if buffer:
                segments.append((section, "\n".join(buffer)))
                buffer = []
            section = line.strip()
        else:
            buffer.append(line)
    if buffer:
        segments.append((section, "\n".join(buffer)))
    if not segments:
        segments.append((section, ""))
    return segments


def _window(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Break text into overlapping windows, snapping to whitespace boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    step = max(chunk_size - overlap, 1)
    windows: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # Snap the end back to the last whitespace to avoid cutting a word.
        if end < n:
            snap = text.rfind(" ", start, end)
            if snap > start:
                end = snap
        piece = text[start:end].strip()
        if piece:
            windows.append(piece)
        if end >= n:
            break
        start += step
    return windows


def chunk_document(
    doc_id: str,
    document_name: str,
    pages: list[tuple[int, str]],
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[DocumentChunk]:
    """Chunk a document's pages into section-tagged :class:`DocumentChunk` spans."""
    chunks: list[DocumentChunk] = []
    index = 0
    current_section: str | None = None

    for page_number, page_text in pages:
        for section, body in _split_into_sections(page_text, current_section):
            current_section = section
            for piece in _window(body, chunk_size, overlap):
                chunks.append(
                    DocumentChunk(
                        doc_id=doc_id,
                        document_name=document_name,
                        text=piece,
                        page_number=page_number,
                        section=section,
                        chunk_index=index,
                    )
                )
                index += 1
    return chunks
