"""Phase E: Scoring and feedback."""
from __future__ import annotations

import math


def _make_store():
    from nodus_memory.config import MemoryConfig
    from nodus_memory.store import MemoryStore
    return MemoryStore(MemoryConfig(tenant_id="alice"))


class TestScoreTracker:
    def test_compute_weight_zero_usage(self):
        from nodus_memory.scoring import ScoreTracker
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        node = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        w = ScoreTracker.compute_weight(node)
        assert w == 0.0

    def test_compute_weight_with_usage(self):
        from nodus_memory.scoring import ScoreTracker
        import dataclasses
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        node = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        node = dataclasses.replace(node, usage_count=10, success_count=8, failure_count=2)
        w = ScoreTracker.compute_weight(node)
        expected = 1.0 * (1 + 0.8) * math.log1p(10)
        assert abs(w - expected) < 1e-9

    def test_higher_success_ratio_gives_higher_weight(self):
        from nodus_memory.scoring import ScoreTracker
        import dataclasses
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        base = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        good = dataclasses.replace(base, usage_count=10, success_count=9, failure_count=1)
        bad = dataclasses.replace(base, usage_count=10, success_count=1, failure_count=9)
        assert ScoreTracker.compute_weight(good) > ScoreTracker.compute_weight(bad)

    def test_higher_impact_score_gives_higher_weight(self):
        from nodus_memory.scoring import ScoreTracker
        import dataclasses
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        base = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        base = dataclasses.replace(base, usage_count=5)
        high = dataclasses.replace(base, impact_score=2.0)
        low = dataclasses.replace(base, impact_score=0.5)
        assert ScoreTracker.compute_weight(high) > ScoreTracker.compute_weight(low)

    def test_record_success_increments_both(self):
        from nodus_memory.scoring import ScoreTracker
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        node = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        delta = ScoreTracker.record_success(node)
        assert delta["success_count"] == 1
        assert delta["usage_count"] == 1

    def test_record_failure_increments_both(self):
        from nodus_memory.scoring import ScoreTracker
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        node = MemoryNode.create(
            tenant_id="t", namespace="n", key="k", value="v",
            path=build_path("t", "n", "general", "k"),
        )
        delta = ScoreTracker.record_failure(node)
        assert delta["failure_count"] == 1
        assert delta["usage_count"] == 1


class TestMemoryStoreFeedback:
    def test_record_success_increments_node(self):
        store = _make_store()
        store.put("k", "v")
        store.record_feedback("k", success=True)
        node = store.get_node("k")
        assert node.success_count == 1
        assert node.usage_count == 1

    def test_record_failure_increments_node(self):
        store = _make_store()
        store.put("k", "v")
        store.record_feedback("k", success=False)
        node = store.get_node("k")
        assert node.failure_count == 1
        assert node.usage_count == 1

    def test_multiple_feedbacks_accumulate(self):
        store = _make_store()
        store.put("k", "v")
        store.record_feedback("k", success=True)
        store.record_feedback("k", success=True)
        store.record_feedback("k", success=False)
        node = store.get_node("k")
        assert node.success_count == 2
        assert node.failure_count == 1
        assert node.usage_count == 3

    def test_recall_all_sort_by_weight(self):
        store = _make_store()
        store.put("low", "v")
        store.put("high", "v")
        store.record_feedback("high", success=True)
        store.record_feedback("high", success=True)
        results = store.recall_all(sort_by="weight")
        keys = [n.key for n in results]
        assert keys.index("high") < keys.index("low")

    def test_feedback_on_missing_key_raises(self):
        from nodus_memory.errors import KeyNotFoundError
        store = _make_store()
        with pytest.raises(KeyNotFoundError):
            store.record_feedback("nonexistent", success=True)


import pytest
