from __future__ import annotations

import abc
from typing import Any

from nodus_memory.model import MemoryNode


class MemoryBackend(abc.ABC):
    """Abstract interface that all storage backends must implement."""

    @abc.abstractmethod
    def put(self, node: MemoryNode) -> MemoryNode:
        """Store or replace a node. Returns the stored node."""

    @abc.abstractmethod
    def get(self, path: str) -> MemoryNode | None:
        """Return the node at *path*, or None if absent."""

    @abc.abstractmethod
    def delete(self, path: str) -> bool:
        """Remove the node at *path*. Return True if it existed."""

    @abc.abstractmethod
    def has(self, path: str) -> bool:
        """Return True if a node exists at *path*."""

    @abc.abstractmethod
    def keys(self, tenant_prefix: str) -> list[str]:
        """Return all keys (not paths) whose path starts with *tenant_prefix*."""

    @abc.abstractmethod
    def recall_by_tag(self, tags: frozenset[str], tenant_prefix: str) -> list[MemoryNode]:
        """Return nodes whose tag set is a superset of *tags* (AND semantics)."""

    @abc.abstractmethod
    def recall_by_path(self, path_prefix: str, limit: int) -> list[MemoryNode]:
        """Return nodes whose path starts with *path_prefix*, up to *limit*."""

    @abc.abstractmethod
    def recall_all(self, tenant_prefix: str, limit: int) -> list[MemoryNode]:
        """Return all nodes under *tenant_prefix*, up to *limit*."""

    @abc.abstractmethod
    def update(self, path: str, **fields: Any) -> MemoryNode | None:
        """Update mutable fields on the node at *path*. Return updated node or None."""
