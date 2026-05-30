from __future__ import annotations

import dataclasses
import time
from typing import Any

from nodus_memory.address import build_path, path_prefix
from nodus_memory.backends.base import MemoryBackend
from nodus_memory.backends.memory import InMemoryBackend
from nodus_memory.config import MemoryConfig
from nodus_memory.embedding import EmbeddingProvider, NoOpProvider, cosine_similarity
from nodus_memory.errors import KeyNotFoundError, TenantError
from nodus_memory.model import MemoryNode


class MemoryStore:
    """Tenant-scoped facade over a MemoryBackend.

    All operations are scoped to the configured tenant_id. Cross-tenant paths
    raise TenantError before touching the backend.
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        backend: MemoryBackend | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self._config = config or MemoryConfig()
        if backend is not None:
            self._backend = backend
        elif self._config.backend == "sqlalchemy":
            from nodus_memory.backends.sqlalchemy import SQLAlchemyBackend
            self._backend = SQLAlchemyBackend(self._config.db_url)
        else:
            self._backend = InMemoryBackend()
        self._embedder: EmbeddingProvider = embedding_provider or NoOpProvider()

    @property
    def tenant_id(self) -> str:
        return self._config.tenant_id

    @property
    def namespace(self) -> str:
        return self._config.namespace

    # --- core CRUD ---

    def put(
        self,
        key: str,
        value: Any,
        *,
        type: str = "general",
        tags: frozenset[str] | None = None,
        namespace: str | None = None,
        impact_score: float = 1.0,
    ) -> MemoryNode:
        ns = namespace or self._config.namespace
        p = build_path(self._config.tenant_id, ns, type, key)
        node = MemoryNode.create(
            tenant_id=self._config.tenant_id,
            namespace=ns,
            key=key,
            value=value,
            path=p,
            type=type,
            tags=tags,
            impact_score=impact_score,
        )
        return self._backend.put(node)

    def get(self, key: str, *, type: str = "general", namespace: str | None = None) -> Any:
        node = self._get_node(key, type=type, namespace=namespace)
        if node is None:
            return None
        self._backend.update(node.path, usage_count=node.usage_count + 1)
        return node.value

    def get_node(self, key: str, *, type: str = "general", namespace: str | None = None) -> MemoryNode | None:
        return self._get_node(key, type=type, namespace=namespace)

    def delete(self, key: str, *, type: str = "general", namespace: str | None = None) -> bool:
        p = self._path(key, type=type, namespace=namespace)
        return self._backend.delete(p)

    def has(self, key: str, *, type: str = "general", namespace: str | None = None) -> bool:
        return self._backend.has(self._path(key, type=type, namespace=namespace))

    def keys(self, *, namespace: str | None = None) -> list[str]:
        prefix = path_prefix(self._config.tenant_id, namespace or self._config.namespace)
        return self._backend.keys(prefix)

    # --- tag operations ---

    def tag(self, key: str, tags: frozenset[str], *, type: str = "general", namespace: str | None = None) -> MemoryNode:
        node = self._require_node(key, type=type, namespace=namespace)
        return self._backend.update(node.path, tags=tags)  # type: ignore[return-value]

    # --- retrieval ---

    def recall_from(self, key: str, *, type: str = "general", namespace: str | None = None) -> Any:
        return self.get(key, type=type, namespace=namespace)

    def recall_all(
        self,
        *,
        tag: str | None = None,
        tags: frozenset[str] | None = None,
        path_prefix_override: str | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        sort_by: str = "created_at",
    ) -> list[MemoryNode]:
        cap = limit if limit is not None else self._config.max_recall_limit
        ns = namespace or self._config.namespace
        prefix = path_prefix_override or path_prefix(self._config.tenant_id, ns)
        self._assert_tenant_prefix(prefix)

        if tag is not None or tags is not None:
            tag_set: frozenset[str] = frozenset()
            if tag is not None:
                tag_set = tag_set | {tag}
            if tags is not None:
                tag_set = tag_set | tags
            nodes = self._backend.recall_by_tag(tag_set, prefix)
        elif path_prefix_override is not None:
            nodes = self._backend.recall_by_path(prefix, limit=cap)
        else:
            nodes = self._backend.recall_all(prefix, limit=cap)

        return self._sort(nodes, sort_by)[:cap]

    def share(self, key: str, value: Any, *, type: str = "general") -> MemoryNode:
        """Store in the 'shared' namespace (cross-agent readable within tenant)."""
        return self.put(key, value, type=type, namespace="shared")

    # --- feedback ---

    def record_feedback(self, key: str, success: bool, *, type: str = "general", namespace: str | None = None) -> None:
        node = self._require_node(key, type=type, namespace=namespace)
        delta: dict[str, Any] = {"usage_count": node.usage_count + 1}
        if success:
            delta["success_count"] = node.success_count + 1
        else:
            delta["failure_count"] = node.failure_count + 1
        self._backend.update(node.path, **delta)

    # --- causal chain ---

    def link(self, child_key: str, parent_key: str, *, type: str = "general", namespace: str | None = None) -> MemoryNode:
        from nodus_memory.errors import CausalCycleError
        child = self._require_node(child_key, type=type, namespace=namespace)
        parent = self._require_node(parent_key, type=type, namespace=namespace)
        if self._would_create_cycle(child.path, parent.id):
            raise CausalCycleError(child_key)
        return self._backend.update(child.path, causal_parent_id=parent.id)  # type: ignore[return-value]

    def recall_chain(self, key: str, *, type: str = "general", namespace: str | None = None, max_depth: int = 10) -> list[MemoryNode]:
        from nodus_memory.errors import CausalCycleError
        node = self._get_node(key, type=type, namespace=namespace)
        if node is None:
            return []
        chain: list[MemoryNode] = [node]
        seen: set[str] = {node.id}
        for _ in range(max_depth - 1):
            current = chain[-1]
            if current.causal_parent_id is None:
                break
            parent = self._get_node_by_id(current.causal_parent_id)
            if parent is None:
                break
            if parent.id in seen:
                raise CausalCycleError(key)
            seen.add(parent.id)
            chain.append(parent)
        chain.reverse()
        return chain

    # --- embedding / similarity ---

    def recall_similar(
        self,
        text: str,
        *,
        top_k: int = 5,
        threshold: float = 0.7,
        namespace: str | None = None,
    ) -> list[MemoryNode]:
        """Return nodes semantically similar to *text* (requires a real EmbeddingProvider).

        With NoOpProvider (the default), this always returns an empty list because
        all-zeros vectors have no meaningful cosine similarity.
        """
        query_vec = self._embedder.embed(text)
        if all(v == 0.0 for v in query_vec):
            return []
        ns = namespace or self._config.namespace
        prefix = path_prefix(self._config.tenant_id, ns)
        nodes = self._backend.recall_all(prefix, limit=10_000)
        scored: list[tuple[float, MemoryNode]] = []
        for node in nodes:
            if node.embedding is None:
                continue
            sim = cosine_similarity(query_vec, node.embedding)
            if sim >= threshold:
                scored.append((sim, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]

    # --- internal helpers ---

    def _path(self, key: str, *, type: str, namespace: str | None) -> str:
        return build_path(self._config.tenant_id, namespace or self._config.namespace, type, key)

    def _get_node(self, key: str, *, type: str, namespace: str | None) -> MemoryNode | None:
        return self._backend.get(self._path(key, type=type, namespace=namespace))

    def _get_node_by_id(self, node_id: str) -> MemoryNode | None:
        prefix = path_prefix(self._config.tenant_id, self._config.namespace)
        for node in self._backend.recall_all(prefix, limit=10_000):
            if node.id == node_id:
                return node
        return None

    def _require_node(self, key: str, *, type: str, namespace: str | None) -> MemoryNode:
        node = self._get_node(key, type=type, namespace=namespace)
        if node is None:
            raise KeyNotFoundError(key)
        return node

    def _assert_tenant_prefix(self, prefix: str) -> None:
        expected = f"/memory/{self._config.tenant_id}/"
        if not prefix.startswith(expected.rstrip("/")):
            raise TenantError(f"prefix {prefix!r} does not belong to tenant {self._config.tenant_id!r}")

    def _would_create_cycle(self, child_path: str, parent_id: str) -> bool:
        child = self._backend.get(child_path)
        if child is None:
            return False
        child_id = child.id
        # Walk up the PARENT's ancestor chain; if we hit the child, linking
        # child → parent would close a cycle.
        seen: set[str] = set()
        current = self._get_node_by_id(parent_id)
        for _ in range(100):
            if current is None:
                return False
            if current.id == child_id:
                return True
            if current.causal_parent_id is None:
                return False
            if current.causal_parent_id in seen:
                return False
            seen.add(current.id)
            current = self._get_node_by_id(current.causal_parent_id)
        return False

    @staticmethod
    def _sort(nodes: list[MemoryNode], sort_by: str) -> list[MemoryNode]:
        if sort_by == "weight":
            from nodus_memory.scoring import ScoreTracker
            return sorted(nodes, key=lambda n: ScoreTracker.compute_weight(n), reverse=True)
        return sorted(nodes, key=lambda n: n.created_at)
