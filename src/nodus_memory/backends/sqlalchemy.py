from __future__ import annotations

import dataclasses
import json
import time
from typing import Any

from nodus_memory.backends.base import MemoryBackend
from nodus_memory.errors import BackendError
from nodus_memory.model import MemoryNode

try:
    import sqlalchemy as sa
    from sqlalchemy import Column, Float, Integer, MetaData, String, Table, Text
    from sqlalchemy import create_engine, select, delete as sa_delete
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False


def _require_sqlalchemy() -> None:
    if not _SA_AVAILABLE:
        raise BackendError(
            "sqlalchemy is required for SQLAlchemyBackend — "
            "install it with: pip install 'nodus-memory[db]'"
        )


class SQLAlchemyBackend(MemoryBackend):
    """SQLAlchemy-backed persistent memory backend (optional [db] extra)."""

    def __init__(self, db_url: str) -> None:
        _require_sqlalchemy()
        self._engine = create_engine(db_url)
        self._meta = MetaData()
        self._nodes = Table(
            "nodus_memory_nodes", self._meta,
            Column("path", String(512), primary_key=True),
            Column("id", String(36), nullable=False),
            Column("tenant_id", String(255), nullable=False),
            Column("namespace", String(255), nullable=False),
            Column("type", String(255), nullable=False),
            Column("key", String(512), nullable=False),
            Column("value_json", Text, nullable=False),
            Column("tags_json", Text, nullable=False, default="[]"),
            Column("created_at", Float, nullable=False),
            Column("updated_at", Float, nullable=False),
            Column("causal_parent_id", String(36), nullable=True),
            Column("embedding_json", Text, nullable=True),
            Column("impact_score", Float, nullable=False, default=1.0),
            Column("usage_count", Integer, nullable=False, default=0),
            Column("success_count", Integer, nullable=False, default=0),
            Column("failure_count", Integer, nullable=False, default=0),
        )
        self._meta.create_all(self._engine)

    def put(self, node: MemoryNode) -> MemoryNode:
        row = self._to_row(node)
        with self._engine.begin() as conn:
            existing = conn.execute(
                select(self._nodes).where(self._nodes.c.path == node.path)
            ).first()
            if existing:
                conn.execute(self._nodes.update().where(
                    self._nodes.c.path == node.path
                ).values(**row))
            else:
                conn.execute(self._nodes.insert().values(**row))
        return node

    def get(self, path: str) -> MemoryNode | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._nodes).where(self._nodes.c.path == path)
            ).first()
        return self._from_row(row) if row else None

    def delete(self, path: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                sa_delete(self._nodes).where(self._nodes.c.path == path)
            )
            return result.rowcount > 0

    def has(self, path: str) -> bool:
        return self.get(path) is not None

    def keys(self, tenant_prefix: str) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._nodes.c.key, self._nodes.c.path).where(
                    self._nodes.c.path.like(tenant_prefix + "%")
                )
            ).fetchall()
        return sorted(r.key for r in rows)

    def recall_by_tag(self, tags: frozenset[str], tenant_prefix: str) -> list[MemoryNode]:
        nodes = self.recall_all(tenant_prefix, limit=10_000)
        return [n for n in nodes if tags <= n.tags]

    def recall_by_path(self, path_prefix: str, limit: int) -> list[MemoryNode]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._nodes).where(
                    self._nodes.c.path.like(path_prefix + "%")
                ).limit(limit)
            ).fetchall()
        return [self._from_row(r) for r in rows]

    def recall_all(self, tenant_prefix: str, limit: int) -> list[MemoryNode]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(self._nodes).where(
                    self._nodes.c.path.like(tenant_prefix + "%")
                ).limit(limit)
            ).fetchall()
        return [self._from_row(r) for r in rows]

    def update(self, path: str, **fields: Any) -> MemoryNode | None:
        node = self.get(path)
        if node is None:
            return None
        updated = dataclasses.replace(node, updated_at=time.time(), **fields)
        self.put(updated)
        return updated

    def _to_row(self, node: MemoryNode) -> dict:
        return {
            "path": node.path,
            "id": node.id,
            "tenant_id": node.tenant_id,
            "namespace": node.namespace,
            "type": node.type,
            "key": node.key,
            "value_json": json.dumps(node.value),
            "tags_json": json.dumps(sorted(node.tags)),
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "causal_parent_id": node.causal_parent_id,
            "embedding_json": json.dumps(node.embedding) if node.embedding is not None else None,
            "impact_score": node.impact_score,
            "usage_count": node.usage_count,
            "success_count": node.success_count,
            "failure_count": node.failure_count,
        }

    def _from_row(self, row: Any) -> MemoryNode:
        embedding = json.loads(row.embedding_json) if row.embedding_json else None
        return MemoryNode(
            id=row.id,
            tenant_id=row.tenant_id,
            namespace=row.namespace,
            type=row.type,
            key=row.key,
            value=json.loads(row.value_json),
            path=row.path,
            created_at=row.created_at,
            updated_at=row.updated_at,
            tags=frozenset(json.loads(row.tags_json)),
            causal_parent_id=row.causal_parent_id,
            embedding=embedding,
            impact_score=row.impact_score,
            usage_count=row.usage_count,
            success_count=row.success_count,
            failure_count=row.failure_count,
        )
