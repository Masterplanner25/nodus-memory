from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryNode:
    """Immutable representation of a single memory entry.

    All updates produce a new MemoryNode via dataclasses.replace().
    """

    id: str
    tenant_id: str
    namespace: str
    type: str
    key: str
    value: Any
    path: str
    created_at: float
    updated_at: float
    tags: frozenset[str] = field(default_factory=frozenset)
    causal_parent_id: str | None = None
    embedding: list[float] | None = None
    impact_score: float = 1.0
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @staticmethod
    def create(
        tenant_id: str,
        namespace: str,
        key: str,
        value: Any,
        path: str,
        *,
        type: str = "general",
        tags: frozenset[str] | None = None,
        causal_parent_id: str | None = None,
        impact_score: float = 1.0,
    ) -> "MemoryNode":
        now = time.time()
        return MemoryNode(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            namespace=namespace,
            type=type,
            key=key,
            value=value,
            path=path,
            created_at=now,
            updated_at=now,
            tags=tags if tags is not None else frozenset(),
            causal_parent_id=causal_parent_id,
            impact_score=impact_score,
        )
