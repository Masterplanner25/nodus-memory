from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryConfig:
    """Configuration for a MemoryStore instance.

    backend: "memory" (default) or "sqlalchemy"
    tenant_id: default tenant for this store instance
    namespace: logical grouping within a tenant (e.g. "agent", "session")
    db_url: SQLAlchemy connection URL; required when backend="sqlalchemy"
    embedding_provider: name of the provider class; "noop" by default
    """

    backend: str = "memory"
    tenant_id: str = "default"
    namespace: str = "default"
    db_url: str = ""
    embedding_provider: str = "noop"
    max_recall_limit: int = 100

    def __post_init__(self) -> None:
        if self.backend not in ("memory", "sqlalchemy"):
            raise ValueError(f"unsupported backend: {self.backend!r}")
        if not self.tenant_id:
            raise ValueError("tenant_id must be a non-empty string")
        if not self.namespace:
            raise ValueError("namespace must be a non-empty string")
        if self.backend == "sqlalchemy" and not self.db_url:
            raise ValueError("db_url is required when backend='sqlalchemy'")
