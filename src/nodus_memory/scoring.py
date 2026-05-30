from __future__ import annotations

import math

from nodus_memory.model import MemoryNode

try:
    import nodus_native_memory_engine as _native_engine
    _NATIVE = True
except ImportError:
    _native_engine = None
    _NATIVE = False


class ScoreTracker:
    """Stateless utility for computing memory node weights.

    Uses nodus-native-memory-engine for Rust-accelerated computation when installed.
    """

    @staticmethod
    def compute_weight(node: MemoryNode) -> float:
        """Compute a ranking weight for the given node.

        weight = impact_score * (1 + success_ratio) * log1p(usage_count)
        """
        if _NATIVE:
            return _native_engine.compute_weight(
                node.impact_score, node.usage_count, node.success_count, node.failure_count
            )
        total = node.success_count + node.failure_count
        success_ratio = node.success_count / total if total > 0 else 0.0
        return node.impact_score * (1.0 + success_ratio) * math.log1p(node.usage_count)

    @staticmethod
    def batch_weights(nodes: list[MemoryNode]) -> list[float]:
        """Compute weights for a batch of nodes efficiently."""
        if _NATIVE:
            return _native_engine.batch_compute_weights([
                (n.impact_score, n.usage_count, n.success_count, n.failure_count)
                for n in nodes
            ])
        return [ScoreTracker.compute_weight(n) for n in nodes]

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
