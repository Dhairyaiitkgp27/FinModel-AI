"""PDF text extraction for the RAG pipeline.

Uses PyMuPDF (``fitz``) to pull text per page, imported lazily so the rest of the
RAG layer works without it installed. A small plain-text reader is also provided
so ``.txt`` filings (and the bundled sample document) can be ingested with no
third-party dependencies at all.
"""
from __future__ import annotations

from pathlib import Path


def extract_pdf_pages(path: str | Path) -> list[tuple[int, str]]:
    """Return ``(page_number, text)`` tuples for each page of a PDF.

    Page numbers are 1-indexed. Requires PyMuPDF; raises a clear error if it is
    not installed.
    """
    try:
        import fitz  # noqa: PLC0415 - intentional lazy import (PyMuPDF)
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "PyMuPDF is required to read PDFs. Install it with `pip install pymupdf`, "
            "or ingest a plain-text (.txt) filing instead."
        ) from exc

    pages: list[tuple[int, str]] = []
    with fitz.open(str(path)) as doc:  # pragma: no cover - needs a real PDF + lib
        for i, page in enumerate(doc, start=1):
            pages.append((i, page.get_text("text")))
    return pages


def extract_text_pages(path: str | Path, page_marker: str = "\f") -> list[tuple[int, str]]:
    """Read a plain-text file into ``(page_number, text)`` tuples.

    Pages are split on ``page_marker`` (a form-feed by default); a file with no
    markers is treated as a single page.
    """
    raw = Path(path).read_text(encoding="utf-8")
    parts = raw.split(page_marker)
    return [(i, part) for i, part in enumerate(parts, start=1)]


def extract_pages(path: str | Path) -> list[tuple[int, str]]:
    """Extract pages, dispatching on file extension (.pdf vs plain text)."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_pages(path)
    return extract_text_pages(path)
