"""Memory scoring — rank nodes by relevance using multiple signals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import MemoryNode


@dataclass
class MemoryScore:
    """Composite relevance score for one memory node."""

    node_id: str
    semantic_score: float = 0.0   # cosine similarity (0–1)
    tag_score: float = 0.0        # fraction of query tags matched
    impact_score: float = 0.0     # node's stored impact_score
    weight: float = 1.0           # node's stored weight (feedback-adjusted)
    usage_penalty: float = 0.0    # small penalty for over-used nodes

    @property
    def total(self) -> float:
        """Weighted composite score."""
        return (
            0.5 * self.semantic_score
            + 0.2 * self.tag_score
            + 0.2 * self.impact_score
            + 0.1 * self.weight
            - 0.05 * self.usage_penalty
        )


def score_nodes(
    nodes: list[MemoryNode],
    *,
    query_tags: Optional[list[str]] = None,
    query_embedding: Optional[list[float]] = None,
) -> list[tuple[MemoryNode, MemoryScore]]:
    """Score and rank *nodes* by composite relevance.

    Args:
        nodes:           Candidate nodes to score.
        query_tags:      Tags from the current query (for tag overlap scoring).
        query_embedding: Embedding of the query text (for semantic scoring).

    Returns:
        List of ``(node, score)`` sorted by ``score.total`` descending.
    """
    results: list[tuple[MemoryNode, MemoryScore]] = []
    tag_set = set(query_tags or [])
    max_usage = max((n.usage_count for n in nodes), default=1) or 1

    for node in nodes:
        score = MemoryScore(node_id=node.id)

        # Semantic score
        if query_embedding and node.embedding:
            score.semantic_score = _cosine_similarity(query_embedding, node.embedding)

        # Tag overlap
        if tag_set and node.tags:
            overlap = len(tag_set & set(node.tags))
            score.tag_score = overlap / len(tag_set)

        score.impact_score = min(1.0, max(0.0, node.impact_score))
        score.weight = min(2.0, max(0.0, node.weight))
        score.usage_penalty = node.usage_count / max_usage

        results.append((node, score))

    results.sort(key=lambda x: x[1].total, reverse=True)
    return results


def update_feedback(node: MemoryNode, *, success: bool) -> None:
    """Update *node*'s feedback counters and weight in-place.

    A simple exponential moving average adjusts weight toward positive or
    negative based on outcome history.
    """
    if success:
        node.success_count += 1
        node.weight = min(2.0, node.weight * 1.05)
    else:
        node.failure_count += 1
        node.weight = max(0.1, node.weight * 0.95)

    total = node.success_count + node.failure_count
    if total > 0:
        node.impact_score = min(1.0, node.success_count / total)
    node.touch()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
