"""MemoryStore protocol and InMemoryStore for tests."""
from __future__ import annotations

import threading
from typing import Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore[assignment]

from .models import MemoryNode


@runtime_checkable
class MemoryStore(Protocol):
    """Persistence layer for MemoryNode objects."""

    def write(self, node: MemoryNode) -> MemoryNode: ...
    def get(self, node_id: str, user_id: str) -> Optional[MemoryNode]: ...
    def search_by_tags(
        self, tags: list[str], user_id: str, limit: int
    ) -> list[MemoryNode]: ...
    def search_by_path(
        self, path_glob: str, user_id: str, limit: int
    ) -> list[MemoryNode]: ...
    def search_semantic(
        self, embedding: list[float], user_id: str, limit: int
    ) -> list[MemoryNode]: ...
    def update_feedback(self, node_id: str, success: bool) -> None: ...
    def delete(self, node_id: str, user_id: str) -> bool: ...
    def list_by_user(self, user_id: str, limit: int = 100) -> list[MemoryNode]: ...


class InMemoryStore:
    """Thread-safe in-process memory store.

    Uses exact tag matching and basic keyword search for ``search_semantic``
    (since there are no real embeddings in tests).
    Suitable for unit tests and single-process development.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, MemoryNode] = {}
        self._lock = threading.Lock()

    def write(self, node: MemoryNode) -> MemoryNode:
        with self._lock:
            self._nodes[node.id] = node
        return node

    def get(self, node_id: str, user_id: str) -> Optional[MemoryNode]:
        with self._lock:
            node = self._nodes.get(node_id)
        if node and node.user_id == user_id:
            return node
        return None

    def search_by_tags(
        self, tags: list[str], user_id: str, limit: int
    ) -> list[MemoryNode]:
        tag_set = set(tags)
        with self._lock:
            candidates = [
                n for n in self._nodes.values()
                if n.user_id == user_id and tag_set.intersection(set(n.tags))
            ]
        candidates.sort(key=lambda n: len(tag_set & set(n.tags)), reverse=True)
        return candidates[:limit]

    def search_by_path(
        self, path_glob: str, user_id: str, limit: int
    ) -> list[MemoryNode]:
        from .address import glob_match  # noqa: PLC0415
        with self._lock:
            candidates = [
                n for n in self._nodes.values()
                if n.user_id == user_id
                and n.path is not None
                and glob_match(n.path, path_glob)
            ]
        return candidates[:limit]

    def search_semantic(
        self, embedding: list[float], user_id: str, limit: int
    ) -> list[MemoryNode]:
        from .scoring import _cosine_similarity  # noqa: PLC0415
        with self._lock:
            candidates = [
                n for n in self._nodes.values()
                if n.user_id == user_id
            ]
        if any(n.embedding for n in candidates):
            scored = [
                (n, _cosine_similarity(embedding, n.embedding or []))
                for n in candidates
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [n for n, _ in scored[:limit]]
        return candidates[:limit]

    def update_feedback(self, node_id: str, success: bool) -> None:
        from .scoring import update_feedback  # noqa: PLC0415
        with self._lock:
            node = self._nodes.get(node_id)
        if node is not None:
            update_feedback(node, success=success)

    def delete(self, node_id: str, user_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node and node.user_id == user_id:
                del self._nodes[node_id]
                return True
        return False

    def list_by_user(self, user_id: str, limit: int = 100) -> list[MemoryNode]:
        with self._lock:
            nodes = [n for n in self._nodes.values() if n.user_id == user_id]
        nodes.sort(key=lambda n: n.created_at, reverse=True)
        return nodes[:limit]

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)
