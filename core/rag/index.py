"""Vector indexes for semantic retrieval.

Two implementations behind a common interface:

* :class:`NumpyIndex` — brute-force cosine similarity over a NumPy matrix.
  Dependency-light (NumPy only), exact, and fast enough for the thousands of
  chunks a filing produces; used by default and fully testable offline.
* :class:`FaissIndex` — a FAISS ``IndexFlatIP`` (lazy import) for larger corpora.

Both expect unit-norm vectors (so inner product equals cosine similarity) and
return the most similar :class:`DocumentChunk` objects with their scores.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.rag import DocumentChunk, RetrievedChunk


class VectorIndex(ABC):
    """Abstract similarity index over document chunks."""

    @abstractmethod
    def add(self, vectors: Any, chunks: list[DocumentChunk]) -> None:
        """Add embedding vectors and their corresponding chunks."""

    @abstractmethod
    def search(self, query_vector: Any, k: int) -> list[RetrievedChunk]:
        """Return the ``k`` most similar chunks to ``query_vector``."""

    @abstractmethod
    def __len__(self) -> int:
        ...


class NumpyIndex(VectorIndex):
    """Exact brute-force cosine-similarity index backed by NumPy."""

    def __init__(self) -> None:
        self._matrix: Any = None
        self._chunks: list[DocumentChunk] = []

    def add(self, vectors: Any, chunks: list[DocumentChunk]) -> None:
        import numpy as np

        vectors = np.asarray(vectors, dtype=float)
        if len(chunks) != vectors.shape[0]:
            raise ValueError("Number of chunks must match number of vectors.")
        if self._matrix is None:
            self._matrix = vectors
        else:
            self._matrix = np.vstack([self._matrix, vectors])
        self._chunks.extend(chunks)

    def search(self, query_vector: Any, k: int) -> list[RetrievedChunk]:
        import numpy as np

        if self._matrix is None or not self._chunks:
            return []
        query = np.asarray(query_vector, dtype=float).reshape(-1)
        scores = self._matrix @ query
        k = min(k, len(self._chunks))
        # Top-k indices, highest score first.
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]
        return [
            RetrievedChunk(chunk=self._chunks[int(i)], score=float(scores[int(i)]))
            for i in top
        ]

    def __len__(self) -> int:
        return len(self._chunks)


class FaissIndex(VectorIndex):
    """FAISS inner-product index (lazy import) for larger corpora."""

    def __init__(self, dim: int):
        self.dim = dim
        self._chunks: list[DocumentChunk] = []
        self._index = self._new_index(dim)

    @staticmethod
    def _new_index(dim: int) -> Any:
        try:
            import faiss  # noqa: PLC0415 - lazy import
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ImportError(
                "The 'faiss-cpu' package is required for FaissIndex. "
                "Install it with `pip install faiss-cpu`, or use NumpyIndex."
            ) from exc
        return faiss.IndexFlatIP(dim)

    def add(self, vectors: Any, chunks: list[DocumentChunk]) -> None:  # pragma: no cover
        import numpy as np

        vectors = np.asarray(vectors, dtype="float32")
        self._index.add(vectors)
        self._chunks.extend(chunks)

    def search(self, query_vector: Any, k: int) -> list[RetrievedChunk]:  # pragma: no cover
        import numpy as np

        if not self._chunks:
            return []
        query = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        k = min(k, len(self._chunks))
        scores, indices = self._index.search(query, k)
        return [
            RetrievedChunk(chunk=self._chunks[int(idx)], score=float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        ]

    def __len__(self) -> int:
        return len(self._chunks)
