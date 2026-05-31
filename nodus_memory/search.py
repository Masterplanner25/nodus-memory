"""High-level memory retrieval functions."""
from __future__ import annotations

from typing import Optional

from .embedding import EmbeddingProvider, NoopEmbeddingProvider
from .models import MemoryNode
from .scoring import score_nodes
from .store import MemoryStore


def recall(
    query: str,
    user_id: str,
    store: MemoryStore,
    *,
    embedder: Optional[EmbeddingProvider] = None,
    limit: int = 5,
    tags: Optional[list[str]] = None,
) -> list[MemoryNode]:
    """Recall the most relevant memory nodes for *query*.

    Strategy:
    1. If *tags* provided: tag search (fast, no embedding needed)
    2. If embedder available: semantic search with embedding
    3. Combine and re-rank by composite score

    Args:
        query:    Natural language query string.
        user_id:  Tenant ID for isolation.
        store:    Memory store backend.
        embedder: Optional embedding provider.
        limit:    Maximum nodes to return.
        tags:     Optional tag filter applied before semantic search.

    Returns:
        Up to *limit* nodes sorted by composite relevance score.
    """
    candidates: list[MemoryNode] = []

    if tags:
        candidates = store.search_by_tags(tags, user_id, limit * 3)

    if embedder is not None and query:
        import asyncio  # noqa: PLC0415
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context — caller should use recall_async
                embedding = [0.0] * embedder.dimensions
            else:
                embedding = loop.run_until_complete(embedder.embed([query]))[0]
        except Exception:
            embedding = [0.0] * embedder.dimensions

        semantic = store.search_semantic(embedding, user_id, limit * 3)
        seen = {n.id for n in candidates}
        candidates.extend(n for n in semantic if n.id not in seen)
    elif not candidates:
        candidates = store.list_by_user(user_id, limit * 3)

    if not candidates:
        return []

    scored = score_nodes(candidates, query_tags=tags)
    return [node for node, _ in scored[:limit]]


async def recall_async(
    query: str,
    user_id: str,
    store: MemoryStore,
    *,
    embedder: Optional[EmbeddingProvider] = None,
    limit: int = 5,
    tags: Optional[list[str]] = None,
) -> list[MemoryNode]:
    """Async version of :func:`recall` — preferred in async contexts."""
    candidates: list[MemoryNode] = []

    if tags:
        candidates = store.search_by_tags(tags, user_id, limit * 3)

    if embedder is not None and query:
        try:
            embeddings = await embedder.embed([query])
            embedding = embeddings[0]
        except Exception:
            embedding = [0.0] * embedder.dimensions
        semantic = store.search_semantic(embedding, user_id, limit * 3)
        seen = {n.id for n in candidates}
        candidates.extend(n for n in semantic if n.id not in seen)
    elif not candidates:
        candidates = store.list_by_user(user_id, limit * 3)

    if not candidates:
        return []

    scored = score_nodes(candidates, query_tags=tags)
    return [node for node, _ in scored[:limit]]
