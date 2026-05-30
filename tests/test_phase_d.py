"""Phase D: Tag-based and path-prefix retrieval."""
from __future__ import annotations

import pytest


def _make_store(tenant="alice", namespace="agent"):
    from nodus_memory.config import MemoryConfig
    from nodus_memory.store import MemoryStore
    return MemoryStore(MemoryConfig(tenant_id=tenant, namespace=namespace))


class TestTagRetrieval:
    def test_recall_by_single_tag(self):
        store = _make_store()
        store.put("a", 1, tags=frozenset({"important"}))
        store.put("b", 2, tags=frozenset({"other"}))
        results = store.recall_all(tag="important")
        keys = [n.key for n in results]
        assert "a" in keys
        assert "b" not in keys

    def test_recall_by_tag_and_semantics(self):
        store = _make_store()
        store.put("both", 1, tags=frozenset({"ai", "critical"}))
        store.put("one", 2, tags=frozenset({"ai"}))
        results = store.recall_all(tags=frozenset({"ai", "critical"}))
        keys = [n.key for n in results]
        assert "both" in keys
        assert "one" not in keys

    def test_recall_by_tag_empty_result(self):
        store = _make_store()
        store.put("k", "v", tags=frozenset({"other"}))
        assert store.recall_all(tag="nonexistent") == []

    def test_tag_operation_replaces_tags(self):
        store = _make_store()
        store.put("k", "v", tags=frozenset({"old"}))
        store.tag("k", frozenset({"new"}))
        results = store.recall_all(tag="new")
        keys = [n.key for n in results]
        assert "k" in keys
        results_old = store.recall_all(tag="old")
        assert "k" not in [n.key for n in results_old]

    def test_tag_on_missing_key_raises(self):
        from nodus_memory.errors import KeyNotFoundError
        store = _make_store()
        with pytest.raises(KeyNotFoundError):
            store.tag("nonexistent", frozenset({"t"}))

    def test_recall_all_no_filter_returns_all(self):
        store = _make_store()
        for i in range(5):
            store.put(f"k{i}", i)
        results = store.recall_all()
        assert len(results) == 5

    def test_recall_all_respects_limit(self):
        store = _make_store()
        for i in range(20):
            store.put(f"k{i}", i)
        results = store.recall_all(limit=5)
        assert len(results) == 5

    def test_recall_all_sorted_by_created_at(self):
        store = _make_store()
        store.put("first", 1)
        store.put("second", 2)
        store.put("third", 3)
        results = store.recall_all()
        keys = [n.key for n in results]
        assert keys.index("first") < keys.index("second") < keys.index("third")


class TestPathPrefixRetrieval:
    def test_recall_by_path_prefix(self):
        from nodus_memory.address import path_prefix_type
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        store = MemoryStore(MemoryConfig(tenant_id="alice", namespace="session"))
        store.put("evt1", "e1", type="event")
        store.put("evt2", "e2", type="event")
        store.put("fact1", "f1", type="fact")

        prefix = path_prefix_type("alice", "session", "event")
        results = store.recall_all(path_prefix_override=prefix)
        keys = [n.key for n in results]
        assert "evt1" in keys
        assert "evt2" in keys
        assert "fact1" not in keys

    def test_recall_by_namespace_prefix(self):
        from nodus_memory.address import path_prefix
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        store = MemoryStore(MemoryConfig(tenant_id="alice", namespace="ns1"))
        store.put("k1", 1, namespace="ns1")
        store.put("k2", 2, namespace="ns2")

        prefix = path_prefix("alice", "ns1")
        results = store.recall_all(path_prefix_override=prefix)
        keys = [n.key for n in results]
        assert "k1" in keys
        assert "k2" not in keys

    def test_recall_all_cross_namespace(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        store = MemoryStore(MemoryConfig(tenant_id="alice", namespace="agent"))
        store.put("k1", 1, namespace="agent")
        store.put("k2", 2, namespace="agent")
        results = store.recall_all(namespace="agent")
        assert len(results) == 2
