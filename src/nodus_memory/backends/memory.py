from __future__ import annotations

import dataclasses
import threading
import time
from typing import Any

from nodus_memory.backends.base import MemoryBackend
from nodus_memory.model import MemoryNode


class InMemoryBackend(MemoryBackend):
    """Thread-safe in-process backend backed by a plain dict."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: dict[str, MemoryNode] = {}

    def put(self, node: MemoryNode) -> MemoryNode:
        with self._lock:
            self._store[node.path] = node
        return node

    def get(self, path: str) -> MemoryNode | None:
        with self._lock:
            return self._store.get(path)

    def delete(self, path: str) -> bool:
        with self._lock:
            existed = path in self._store
            if existed:
                del self._store[path]
            return existed

    def has(self, path: str) -> bool:
        with self._lock:
            return path in self._store

    def keys(self, tenant_prefix: str) -> list[str]:
        with self._lock:
            return sorted(
                node.key
                for node in self._store.values()
                if node.path.startswith(tenant_prefix)
            )

    def recall_by_tag(self, tags: frozenset[str], tenant_prefix: str) -> list[MemoryNode]:
        with self._lock:
            return [
                node
                for node in self._store.values()
                if node.path.startswith(tenant_prefix) and tags <= node.tags
            ]

    def recall_by_path(self, path_prefix: str, limit: int) -> list[MemoryNode]:
        with self._lock:
            matches = [
                node
                for node in self._store.values()
                if node.path.startswith(path_prefix)
            ]
        return matches[:limit]

    def recall_all(self, tenant_prefix: str, limit: int) -> list[MemoryNode]:
        with self._lock:
            return [
                node
                for node in self._store.values()
                if node.path.startswith(tenant_prefix)
            ][:limit]

    def update(self, path: str, **fields: Any) -> MemoryNode | None:
        with self._lock:
            node = self._store.get(path)
            if node is None:
                return None
            updated = dataclasses.replace(node, updated_at=time.time(), **fields)
            self._store[path] = updated
            return updated

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
