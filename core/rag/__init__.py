"""Document RAG: chunking, embeddings, indexing, and cited retrieval/answering."""
from __future__ import annotations

from .chunking import chunk_document
from .embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from .engine import (
    Answerer,
    ExtractiveAnswerer,
    OpenAIAnswerer,
    RAGEngine,
    build_rag_engine,
)
from .index import FaissIndex, NumpyIndex, VectorIndex
from .pdf import extract_pages, extract_pdf_pages, extract_text_pages

__all__ = [
    "chunk_document",
    "Embedder",
    "HashingEmbedder",
    "OpenAIEmbedder",
    "VectorIndex",
    "NumpyIndex",
    "FaissIndex",
    "extract_pages",
    "extract_pdf_pages",
    "extract_text_pages",
    "Answerer",
    "ExtractiveAnswerer",
    "OpenAIAnswerer",
    "RAGEngine",
    "build_rag_engine",
]
