"""EmbeddingProvider protocol and built-in implementations."""
from __future__ import annotations

from typing import Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore[assignment]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding text into dense vectors."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...


class NoopEmbeddingProvider:
    """No-op provider that returns zero vectors.

    Used as a fallback when no real embedding provider is configured.
    All semantic searches will score 0.0, but the system remains functional.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimensions for _ in texts]

    @property
    def dimensions(self) -> int:
        return self._dimensions


class OpenAIEmbeddingProvider:
    """Embedding provider backed by the OpenAI embeddings API.

    Raises:
        ImportError: If the ``openai`` package is not installed.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        try:
            from openai import AsyncOpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "openai package required. Install with: pip install 'nodus-memory[openai]'"
            ) from exc
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model, input=texts
        )
        return [item.embedding for item in response.data]

    @property
    def dimensions(self) -> int:
        return self._dimensions
