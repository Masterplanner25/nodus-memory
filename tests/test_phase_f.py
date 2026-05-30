"""Phase F: Causal chain — link, recall_chain, cycle detection."""
from __future__ import annotations

import pytest


def _make_store():
    from nodus_memory.config import MemoryConfig
    from nodus_memory.store import MemoryStore
    return MemoryStore(MemoryConfig(tenant_id="alice"))


class TestCausalLink:
    def test_link_sets_causal_parent(self):
        store = _make_store()
        store.put("parent", "p-value")
        store.put("child", "c-value")
        store.link("child", "parent")
        child_node = store.get_node("child")
        parent_node = store.get_node("parent")
        assert child_node.causal_parent_id == parent_node.id

    def test_link_missing_child_raises(self):
        from nodus_memory.errors import KeyNotFoundError
        store = _make_store()
        store.put("parent", "v")
        with pytest.raises(KeyNotFoundError):
            store.link("nonexistent-child", "parent")

    def test_link_missing_parent_raises(self):
        from nodus_memory.errors import KeyNotFoundError
        store = _make_store()
        store.put("child", "v")
        with pytest.raises(KeyNotFoundError):
            store.link("child", "nonexistent-parent")


class TestRecallChain:
    def test_recall_chain_single_node(self):
        store = _make_store()
        store.put("k", "v")
        chain = store.recall_chain("k")
        assert len(chain) == 1
        assert chain[0].key == "k"

    def test_recall_chain_linear(self):
        store = _make_store()
        store.put("root", "r")
        store.put("mid", "m")
        store.put("leaf", "l")
        store.link("mid", "root")
        store.link("leaf", "mid")
        chain = store.recall_chain("leaf")
        keys = [n.key for n in chain]
        assert keys == ["root", "mid", "leaf"]

    def test_recall_chain_missing_key_returns_empty(self):
        store = _make_store()
        chain = store.recall_chain("nonexistent")
        assert chain == []

    def test_recall_chain_respects_max_depth(self):
        store = _make_store()
        keys = [f"n{i}" for i in range(10)]
        for k in keys:
            store.put(k, k)
        for i in range(1, len(keys)):
            store.link(keys[i], keys[i - 1])
        chain = store.recall_chain(keys[-1], max_depth=3)
        assert len(chain) <= 3

    def test_recall_chain_no_parent_stops(self):
        store = _make_store()
        store.put("root", "v")
        store.put("child", "v")
        store.link("child", "root")
        chain = store.recall_chain("child")
        assert len(chain) == 2
        assert chain[0].key == "root"
        assert chain[1].key == "child"


class TestCausalCycleDetection:
    def test_direct_cycle_raises(self):
        from nodus_memory.errors import CausalCycleError
        store = _make_store()
        store.put("a", "v")
        store.put("b", "v")
        store.link("a", "b")
        with pytest.raises(CausalCycleError):
            store.link("b", "a")

    def test_recall_chain_detects_cycle(self):
        from nodus_memory.errors import CausalCycleError
        import dataclasses
        from nodus_memory.backends.memory import InMemoryBackend
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        backend = InMemoryBackend()
        store = MemoryStore(MemoryConfig(tenant_id="alice"), backend=backend)
        store.put("a", "v")
        store.put("b", "v")
        store.link("b", "a")
        # Manually create a cycle by updating a's causal_parent_id to b's id
        node_a = store.get_node("a")
        node_b = store.get_node("b")
        backend.update(node_a.path, causal_parent_id=node_b.id)
        with pytest.raises(CausalCycleError):
            store.recall_chain("b")
