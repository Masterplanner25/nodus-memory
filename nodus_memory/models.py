"""MemoryNode and MemoryLink dataclasses."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

VALID_NODE_TYPES: frozenset[str] = frozenset(
    {"decision", "outcome", "insight", "relationship", "execution"}
)
VALID_MEMORY_TYPES: frozenset[str] = frozenset(
    {"decision", "outcome", "failure", "insight"}
)


@dataclass
class MemoryNode:
    """One unit of persistent agent memory.

    Attributes
    ----------
    id:           Unique identifier (UUID string).
    content:      Text content of the memory node.
    tags:         Free-form labels for tag-based retrieval.
    node_type:    Structural type (see VALID_NODE_TYPES).
    user_id:      Tenant/owner ID for isolation.
    memory_type:  Semantic category (see VALID_MEMORY_TYPES).
    path:         Optional MAS path: ``/memory/{tenant}/{ns}/{type}/{id}``.
    namespace:    Optional namespace within MAS.
    impact_score: Importance score (higher = more relevant). 0.0–1.0.
    weight:       Retrieval weight, updated by feedback. 1.0 = neutral.
    success_count: Times this node contributed to a successful outcome.
    failure_count: Times this node contributed to a failure.
    usage_count:   Total recall count.
    embedding:     Optional vector embedding (list of floats).
    source:        Origin identifier (agent ID, flow name, etc.).
    extra:         Arbitrary extra metadata.
    created_at:   UTC creation timestamp.
    updated_at:   UTC last-update timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    tags: list[str] = field(default_factory=list)
    node_type: str = "insight"
    user_id: str = ""
    memory_type: str = "insight"
    path: Optional[str] = None
    namespace: Optional[str] = None
    impact_score: float = 0.0
    weight: float = 1.0
    success_count: int = 0
    failure_count: int = 0
    usage_count: int = 0
    embedding: Optional[list[float]] = None
    source: Optional[str] = None
    extra: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class MemoryLink:
    """A directed causal or associative link between two MemoryNodes."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str = ""
    target_node_id: str = ""
    link_type: str = "related"   # related | caused_by | led_to | similar
    weight: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
