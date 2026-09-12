"""Document-RAG models.

Chunks preserve provenance (document, page, section) so answers can be
source-grounded. Embeddings themselves live in the FAISS index, not in these
schemas; ``DocumentChunk`` optionally carries one only when convenient.
"""
from __future__ import annotations

from pydantic import Field

from .base import FinBaseModel


class DocumentChunk(FinBaseModel):
    """A retrievable, source-attributed span of text from a filing."""

    doc_id: str
    document_name: str
    text: str
    page_number: int | None = None
    section: str | None = None
    chunk_index: int = 0
    embedding: list[float] | None = None

    def citation(self) -> str:
        """Short human-readable source reference."""
        if self.page_number is not None:
            return f"{self.document_name}, p.{self.page_number}"
        return self.document_name


class RetrievedChunk(FinBaseModel):
    """A chunk returned by semantic retrieval, with its similarity score."""

    chunk: DocumentChunk
    score: float


class RAGAnswer(FinBaseModel):
    """An answer grounded in retrieved filing evidence."""

    question: str
    answer: str
    sources: list[RetrievedChunk] = Field(default_factory=list)

    @property
    def citations(self) -> list[str]:
        return [s.chunk.citation() for s in self.sources]
