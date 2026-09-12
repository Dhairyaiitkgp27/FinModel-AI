"""Tests for the RAG layer (chunking, embeddings, index, engine)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.models import DocumentChunk
from core.rag import (
    ExtractiveAnswerer,
    HashingEmbedder,
    NumpyIndex,
    RAGEngine,
    build_rag_engine,
    chunk_document,
)
from core.rag.pdf import extract_pages, extract_text_pages

SAMPLE_DOC = Path(__file__).resolve().parents[1] / "data" / "sample" / "SAMPLE_10K.txt"


# --------------------------------------------------------------------------- #
# Chunking                                                                    #
# --------------------------------------------------------------------------- #
def test_chunking_detects_sections():
    pages = extract_text_pages(SAMPLE_DOC)
    chunks = chunk_document("d", "Nimbus 10-K", pages)
    sections = {c.section for c in chunks}
    assert "Item 1. Business" in sections
    assert "Item 1A. Risk Factors" in sections
    assert any(s and s.startswith("Item 7.") for s in sections)


def test_chunking_windows_long_text_with_bounds():
    text = "word " * 400  # 2000 chars
    chunks = chunk_document("d", "Doc", [(1, text)], chunk_size=200, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 200
    # chunk indices are sequential
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunking_preserves_page_numbers():
    chunks = chunk_document("d", "Doc", [(1, "alpha text one"), (2, "beta text two")])
    assert {c.page_number for c in chunks} == {1, 2}


def test_short_text_is_single_chunk():
    chunks = chunk_document("d", "Doc", [(1, "just a short sentence")])
    assert len(chunks) == 1
    assert chunks[0].text == "just a short sentence"


# --------------------------------------------------------------------------- #
# Embeddings                                                                  #
# --------------------------------------------------------------------------- #
def test_hashing_embedder_is_deterministic_and_normalized():
    emb = HashingEmbedder(dim=128)
    a = emb.embed(["the quick brown fox"])
    b = emb.embed(["the quick brown fox"])
    assert np.allclose(a, b)
    assert np.linalg.norm(a[0]) == pytest.approx(1.0)


def test_hashing_embedder_similarity():
    emb = HashingEmbedder(dim=256)
    v = emb.embed(
        ["cloud platform revenue growth", "cloud platform revenue growth", "zebra igloo umbrella"]
    )
    assert float(v[0] @ v[1]) == pytest.approx(1.0)  # identical
    assert float(v[0] @ v[2]) < 0.2  # disjoint vocabulary


def test_empty_text_embeds_without_error():
    emb = HashingEmbedder(dim=64)
    v = emb.embed([""])
    assert v.shape == (1, 64)
    assert np.linalg.norm(v[0]) == pytest.approx(0.0)  # no tokens -> zero vector


# --------------------------------------------------------------------------- #
# Index                                                                       #
# --------------------------------------------------------------------------- #
def test_numpy_index_search_orders_by_score():
    index = NumpyIndex()
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])
    chunks = [DocumentChunk(doc_id="d", document_name="Doc", text=f"c{i}") for i in range(3)]
    index.add(vectors, chunks)
    results = index.search(np.array([1.0, 0.0]), k=3)
    assert len(results) == 3
    # first vector aligns perfectly -> top; scores descending
    assert results[0].chunk.text == "c0"
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_numpy_index_empty_returns_nothing():
    assert NumpyIndex().search(np.array([1.0, 0.0]), k=5) == []


def test_numpy_index_rejects_mismatched_lengths():
    index = NumpyIndex()
    with pytest.raises(ValueError):
        index.add(np.array([[1.0, 0.0], [0.0, 1.0]]), [DocumentChunk(doc_id="d", document_name="D", text="x")])


# --------------------------------------------------------------------------- #
# Engine (end-to-end retrieval + citations)                                   #
# --------------------------------------------------------------------------- #
@pytest.fixture
def engine() -> RAGEngine:
    eng = build_rag_engine()
    eng.ingest_file(SAMPLE_DOC, doc_id="NMBS", document_name="Nimbus 10-K (sample)")
    return eng


def test_engine_ingests_and_indexes(engine: RAGEngine):
    assert len(engine) >= 3  # at least one chunk per major section


def test_retrieval_routes_to_correct_section(engine: RAGEngine):
    risk = engine.retrieve("cybersecurity data breach supply chain suppliers", top_k=1)[0]
    assert risk.chunk.section == "Item 1A. Risk Factors"

    liquidity = engine.retrieve("liquidity cash capital expenditure next twelve months", top_k=1)[0]
    assert liquidity.chunk.section.startswith("Item 7.")

    business = engine.retrieve("partner channel resellers systems integrators", top_k=1)[0]
    assert business.chunk.section == "Item 1. Business"


def test_answer_carries_citations(engine: RAGEngine):
    answer = engine.answer("What are the risk factors?", top_k=2)
    assert answer.question == "What are the risk factors?"
    assert len(answer.sources) == 2
    assert len(answer.citations) == 2
    assert all("Nimbus 10-K (sample)" in c for c in answer.citations)
    assert all("p.1" in c for c in answer.citations)


def test_extractive_answer_includes_evidence(engine: RAGEngine):
    answer = engine.answer("supply chain risk", top_k=1)
    # extractive answerer echoes the retrieved passage with a bracketed citation
    assert "[1]" in answer.answer
    assert "Nimbus 10-K (sample)" in answer.answer


def test_extractive_answerer_handles_no_results():
    text = ExtractiveAnswerer().answer("anything", [])
    assert "No relevant passages" in text


def test_ingest_text_single_page():
    eng = build_rag_engine()
    count = eng.ingest_text("d", "Note", "A short standalone note about revenue.")
    assert count == 1
    assert eng.retrieve("revenue", top_k=1)[0].chunk.page_number == 1


# --------------------------------------------------------------------------- #
# PDF / text extraction                                                       #
# --------------------------------------------------------------------------- #
def test_extract_text_pages_splits_on_form_feed(tmp_path: Path):
    p = tmp_path / "doc.txt"
    p.write_text("page one text\fpage two text", encoding="utf-8")
    pages = extract_text_pages(p)
    assert len(pages) == 2
    assert pages[0] == (1, "page one text")
    assert pages[1] == (2, "page two text")


def test_extract_pages_dispatches_on_extension(tmp_path: Path):
    p = tmp_path / "doc.txt"
    p.write_text("single page", encoding="utf-8")
    assert extract_pages(p) == [(1, "single page")]


def test_build_rag_engine_defaults_to_offline_stack():
    eng = build_rag_engine()
    assert isinstance(eng.embedder, HashingEmbedder)
    assert isinstance(eng.index, NumpyIndex)
    assert isinstance(eng.answerer, ExtractiveAnswerer)
