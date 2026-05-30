from __future__ import annotations

import math

from nodus_memory.model import MemoryNode


class ScoreTracker:
    """Stateless utility for computing memory node weights."""

    @staticmethod
    def compute_weight(node: MemoryNode) -> float:
        """Compute a ranking weight for the given node.

        weight = impact_score * (1 + success_ratio) * log1p(usage_count)
        """
        total = node.success_count + node.failure_count
        success_ratio = node.success_count / total if total > 0 else 0.0
        return node.impact_score * (1.0 + success_ratio) * math.log1p(node.usage_count)

    @staticmethod
    def record_success(node: MemoryNode) -> dict:
        return {
            "success_count": node.success_count + 1,
            "usage_count": node.usage_count + 1,
        }

    @staticmethod
    def record_failure(node: MemoryNode) -> dict:
        return {
            "failure_count": node.failure_count + 1,
            "usage_count": node.usage_count + 1,
        }
