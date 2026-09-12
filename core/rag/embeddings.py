"""Text embedding providers.

Two implementations behind a common interface:

* :class:`HashingEmbedder` — a deterministic, dependency-light embedder using the
  feature-hashing ("hashing vectoriser") technique: tokens are hashed into a
  fixed-dimensional vector with signed buckets, then L2-normalised. It captures
  lexical overlap, so semantically related passages score highly against a query.
  This makes the whole retrieval pipeline runnable and testable offline.
* :class:`OpenAIEmbedder` — calls the OpenAI embeddings API (lazy import) for
  production-quality semantic embeddings.

Both return an ``(n, dim)`` NumPy array of unit-norm row vectors, so cosine
similarity reduces to a dot product.
"""
from __future__ import annotations

import re
import zlib
from abc import ABC, abstractmethod
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Embedder(ABC):
    """Abstract text embedder."""

    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> Any:
        """Return an ``(len(texts), dim)`` array of unit-norm embeddings."""


class HashingEmbedder(Embedder):
    """Deterministic local embeddings via signed feature hashing."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _hash_bucket(self, token: str) -> tuple[int, float]:
        h = zlib.crc32(token.encode("utf-8"))
        bucket = h % self.dim
        sign = 1.0 if (zlib.crc32(b"sign:" + token.encode("utf-8")) & 1) else -1.0
        return bucket, sign

    def embed(self, texts: list[str]) -> Any:
        import numpy as np

        matrix = np.zeros((len(texts), self.dim), dtype=float)
        for i, text in enumerate(texts):
            for token in _tokenize(text):
                bucket, sign = self._hash_bucket(token)
                matrix[i, bucket] += sign
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class OpenAIEmbedder(Embedder):
    """OpenAI embeddings API provider (lazy import)."""

    def __init__(self, model: str = "text-embedding-3-small", dim: int = 1536):
        self.model = model
        self.dim = dim
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # noqa: PLC0415 - lazy import
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ImportError(
                    "The 'openai' package is required for OpenAI embeddings. "
                    "Install it with `pip install openai`, or use HashingEmbedder."
                ) from exc
            self._client = OpenAI()
        return self._client

    def embed(self, texts: list[str]) -> Any:  # pragma: no cover - needs network/key
        import numpy as np

        client = self._get_client()
        response = client.embeddings.create(model=self.model, input=texts)
        vectors = np.array([item.embedding for item in response.data], dtype=float)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms
