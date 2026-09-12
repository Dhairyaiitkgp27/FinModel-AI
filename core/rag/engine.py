"""The RAG engine: ingest filings, retrieve relevant passages, answer with citations.

The engine ties chunking, embedding, and indexing together. Retrieval is the
substantive, deterministic part and is fully testable offline. Answer synthesis
is pluggable:

* :class:`ExtractiveAnswerer` — builds an answer directly from the retrieved
  passages (no LLM), so the retrieve-and-cite flow works with zero external
  dependencies.
* :class:`OpenAIAnswerer` — prompts an OpenAI model to synthesise a grounded
  answer that cites the numbered sources (lazy import).

Either way the returned :class:`RAGAnswer` carries the retrieved chunks as
``sources``, so citations always point at real, retrieved passages — the engine
never invents a source.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models.rag import RAGAnswer, RetrievedChunk
from .chunking import chunk_document
from .embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from .index import NumpyIndex, VectorIndex
from .pdf import extract_pages

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_TOP_K = 5


class Answerer(ABC):
    """Turns a question plus retrieved passages into an answer string."""

    @abstractmethod
    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> str:
        ...


class ExtractiveAnswerer(Answerer):
    """Compose an answer from the retrieved passages, with no LLM."""

    def __init__(self, max_chars: int = 600):
        self.max_chars = max_chars

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> str:
        if not retrieved:
            return "No relevant passages were found in the indexed documents."
        lines = ["Based on the most relevant passages in the filings:"]
        for i, item in enumerate(retrieved, start=1):
            snippet = " ".join(item.chunk.text.split())[: self.max_chars]
            lines.append(f"[{i}] ({item.chunk.citation()}) {snippet}")
        return "\n".join(lines)


class OpenAIAnswerer(Answerer):
    """Synthesise a grounded, cited answer with an OpenAI chat model (lazy import)."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # noqa: PLC0415 - lazy import
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ImportError(
                    "The 'openai' package is required for OpenAIAnswerer. "
                    "Install it with `pip install openai`, or use ExtractiveAnswerer."
                ) from exc
            self._client = OpenAI()
        return self._client

    def answer(self, question: str, retrieved: list[RetrievedChunk]) -> str:  # pragma: no cover
        if not retrieved:
            return "No relevant passages were found in the indexed documents."
        context = "\n\n".join(
            f"[{i}] ({item.chunk.citation()})\n{item.chunk.text}"
            for i, item in enumerate(retrieved, start=1)
        )
        system = (
            "You are a financial research assistant. Answer the question using ONLY the "
            "numbered sources provided. Cite sources inline as [1], [2], etc. If the "
            "sources do not contain the answer, say so. Do not invent facts or citations."
        )
        user = f"Sources:\n{context}\n\nQuestion: {question}"
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return response.choices[0].message.content or ""


class RAGEngine:
    """Ingests filings and answers questions against them with citations."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        index: VectorIndex | None = None,
        answerer: Answerer | None = None,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
        top_k: int = DEFAULT_TOP_K,
    ):
        self.embedder = embedder or HashingEmbedder()
        self.index = index or NumpyIndex()
        self.answerer = answerer or ExtractiveAnswerer()
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.top_k = top_k

    # --- Ingestion ------------------------------------------------------ #
    def ingest_pages(
        self, doc_id: str, document_name: str, pages: list[tuple[int, str]]
    ) -> int:
        """Chunk, embed, and index a document's pages. Returns the chunk count."""
        chunks = chunk_document(
            doc_id, document_name, pages, chunk_size=self.chunk_size, overlap=self.overlap
        )
        if not chunks:
            return 0
        vectors = self.embedder.embed([c.text for c in chunks])
        enriched = [
            c.model_copy(update={"embedding": [float(x) for x in vectors[i]]})
            for i, c in enumerate(chunks)
        ]
        self.index.add(vectors, enriched)
        return len(enriched)

    def ingest_text(self, doc_id: str, document_name: str, text: str) -> int:
        """Ingest a single block of text as a one-page document."""
        return self.ingest_pages(doc_id, document_name, [(1, text)])

    def ingest_file(
        self, path: str | Path, *, doc_id: str | None = None, document_name: str | None = None
    ) -> int:
        """Ingest a PDF or plain-text filing from disk."""
        path = Path(path)
        pages = extract_pages(path)
        return self.ingest_pages(
            doc_id or path.stem, document_name or path.name, pages
        )

    # --- Retrieval / answering ------------------------------------------ #
    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the most relevant chunks for ``query``."""
        vector = self.embedder.embed([query])[0]
        return self.index.search(vector, top_k or self.top_k)

    def answer(self, question: str, top_k: int | None = None) -> RAGAnswer:
        """Retrieve evidence and synthesise a cited answer."""
        retrieved = self.retrieve(question, top_k)
        text = self.answerer.answer(question, retrieved)
        return RAGAnswer(question=question, answer=text, sources=retrieved)

    def __len__(self) -> int:
        return len(self.index)


def build_rag_engine(
    settings=None,
    *,
    use_openai: bool = False,
) -> RAGEngine:
    """Construct a RAG engine, wiring OpenAI providers when requested and available.

    Defaults to the fully-offline stack (hashing embeddings + NumPy index +
    extractive answers). When ``use_openai`` is set and settings report an API
    key, uses OpenAI embeddings and answer synthesis instead.
    """
    chunk_size = getattr(settings, "rag_chunk_size", DEFAULT_CHUNK_SIZE) if settings else DEFAULT_CHUNK_SIZE
    overlap = getattr(settings, "rag_chunk_overlap", DEFAULT_CHUNK_OVERLAP) if settings else DEFAULT_CHUNK_OVERLAP
    top_k = getattr(settings, "rag_top_k", DEFAULT_TOP_K) if settings else DEFAULT_TOP_K

    if use_openai and settings is not None and getattr(settings, "has_openai", lambda: False)():
        embed_model = getattr(settings, "openai_embedding_model", "text-embedding-3-small")
        chat_model = getattr(settings, "openai_model", "gpt-4o-mini")
        return RAGEngine(
            embedder=OpenAIEmbedder(model=embed_model),
            answerer=OpenAIAnswerer(model=chat_model),
            chunk_size=chunk_size,
            overlap=overlap,
            top_k=top_k,
        )

    return RAGEngine(chunk_size=chunk_size, overlap=overlap, top_k=top_k)
