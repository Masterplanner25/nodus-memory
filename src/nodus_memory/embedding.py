from __future__ import annotations

import abc
import math

try:
    import nodus_native_memory_engine as _native_engine
    _NATIVE = True
except ImportError:
    _native_engine = None
    _NATIVE = False


def _using_native_engine() -> bool:
    """Return True if nodus-native-memory-engine is available."""
    return _NATIVE


class EmbeddingProvider(abc.ABC):
    """Abstract embedding provider.

    Implement this to plug in OpenAI, Cohere, or any other embedding service.
    The library ships only the NoOpProvider; real providers are v0.2+.
    """

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a fixed-length float vector for *text*."""

    @property
    @abc.abstractmethod
    def dimensions(self) -> int:
        """Number of dimensions in the embedding vector."""


class NoOpProvider(EmbeddingProvider):
    """Returns an all-zeros vector. Used when no real provider is configured.

    With this provider, recall_similar() always returns an empty list because
    all-zeros cosine similarity is undefined. This is the safe default.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return [0.0] * self._dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Uses the Rust native engine when nodus-native-memory-engine is installed;
    falls back to pure Python otherwise.
    """
    if _NATIVE:
        return _native_engine.cosine_similarity(a, b)
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)
