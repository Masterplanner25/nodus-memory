"""Phase G: SQLAlchemy persistence backend (sqlite:///:memory:)."""
from __future__ import annotations

import pytest

sa = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed — skip Phase G")


def _make_sa_backend():
    from nodus_memory.backends.sqlalchemy import SQLAlchemyBackend
    return SQLAlchemyBackend("sqlite:///:memory:")


def _make_sa_store(tenant="alice", namespace="agent"):
    from nodus_memory.config import MemoryConfig
    from nodus_memory.store import MemoryStore
    return MemoryStore(
        MemoryConfig(tenant_id=tenant, namespace=namespace, backend="sqlalchemy", db_url="sqlite:///:memory:"),
    )


def _node(key="k", value="v", tenant="t", ns="n", type="general"):
    from nodus_memory.model import MemoryNode
    from nodus_memory.address import build_path
    return MemoryNode.create(
        tenant_id=tenant, namespace=ns, key=key, value=value,
        path=build_path(tenant, ns, type, key), type=type
    )


class TestSQLAlchemyBackendCRUD:
    def test_put_and_get(self):
        b = _make_sa_backend()
        node = _node()
        b.put(node)
        got = b.get(node.path)
        assert got is not None
        assert got.key == "k"
        assert got.value == "v"

    def test_get_missing_returns_none(self):
        b = _make_sa_backend()
        assert b.get("/memory/x/y/z/missing") is None

    def test_has_true(self):
        b = _make_sa_backend()
        node = _node()
        b.put(node)
        assert b.has(node.path)

    def test_has_false(self):
        b = _make_sa_backend()
        assert not b.has("/memory/x/y/z/no")

    def test_delete_returns_true(self):
        b = _make_sa_backend()
        node = _node()
        b.put(node)
        assert b.delete(node.path)

    def test_delete_returns_false_when_absent(self):
        b = _make_sa_backend()
        assert not b.delete("/memory/x/y/z/no")

    def test_delete_removes_node(self):
        b = _make_sa_backend()
        node = _node()
        b.put(node)
        b.delete(node.path)
        assert b.get(node.path) is None

    def test_put_overwrites(self):
        import dataclasses
        b = _make_sa_backend()
        node = _node(value="v1")
        b.put(node)
        updated = dataclasses.replace(node, value="v2")
        b.put(updated)
        got = b.get(node.path)
        assert got.value == "v2"

    def test_keys_lists_under_prefix(self):
        b = _make_sa_backend()
        for k in ("a", "b", "c"):
            b.put(_node(key=k))
        keys = b.keys("/memory/t/n")
        assert set(keys) == {"a", "b", "c"}

    def test_update_fields(self):
        b = _make_sa_backend()
        node = _node()
        b.put(node)
        updated = b.update(node.path, usage_count=7)
        assert updated is not None
        assert updated.usage_count == 7
        got = b.get(node.path)
        assert got.usage_count == 7

    def test_update_missing_returns_none(self):
        b = _make_sa_backend()
        assert b.update("/memory/x/y/z/no", usage_count=1) is None

    def test_recall_by_tag(self):
        import dataclasses
        b = _make_sa_backend()
        b.put(_node(key="tagged", value="v"))
        node = b.get("/memory/t/n/general/tagged")
        updated = dataclasses.replace(node, tags=frozenset({"important"}))
        b.put(updated)
        results = b.recall_by_tag(frozenset({"important"}), "/memory/t/n")
        assert any(n.key == "tagged" for n in results)

    def test_recall_by_path(self):
        b = _make_sa_backend()
        for k in ("a", "b"):
            b.put(_node(key=k))
        results = b.recall_by_path("/memory/t/n", limit=10)
        keys = {n.key for n in results}
        assert {"a", "b"} <= keys

    def test_recall_all(self):
        b = _make_sa_backend()
        for k in ("x", "y", "z"):
            b.put(_node(key=k))
        results = b.recall_all("/memory/t/n", limit=10)
        assert len(results) == 3

    def test_tags_round_trip(self):
        b = _make_sa_backend()
        import dataclasses
        node = _node()
        node = dataclasses.replace(node, tags=frozenset({"a", "b", "c"}))
        b.put(node)
        got = b.get(node.path)
        assert got.tags == frozenset({"a", "b", "c"})

    def test_complex_value_round_trip(self):
        b = _make_sa_backend()
        val = {"nested": [1, 2, {"x": True}], "num": 3.14}
        from nodus_memory.address import build_path
        from nodus_memory.model import MemoryNode
        node = MemoryNode.create(
            tenant_id="t", namespace="n", key="complex", value=val,
            path=build_path("t", "n", "general", "complex"),
        )
        b.put(node)
        got = b.get(node.path)
        assert got.value == val


class TestSQLAlchemyStoreAPI:
    """Replay MemoryStore CRUD tests against the SQLAlchemy backend."""

    def test_put_get(self):
        store = _make_sa_store()
        store.put("k", "v")
        assert store.get("k") == "v"

    def test_has(self):
        store = _make_sa_store()
        store.put("k", "v")
        assert store.has("k")

    def test_delete(self):
        store = _make_sa_store()
        store.put("k", "v")
        store.delete("k")
        assert store.get("k") is None

    def test_tenant_isolation(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        alice = MemoryStore(MemoryConfig(
            tenant_id="alice", backend="sqlalchemy", db_url="sqlite:///:memory:"
        ))
        bob = MemoryStore(MemoryConfig(
            tenant_id="bob", backend="sqlalchemy", db_url="sqlite:///:memory:"
        ))
        alice.put("secret", "alice-val")
        assert bob.get("secret") is None

    def test_recall_all(self):
        store = _make_sa_store()
        store.put("a", 1)
        store.put("b", 2)
        results = store.recall_all()
        assert len(results) == 2

    def test_feedback_persisted(self):
        store = _make_sa_store()
        store.put("k", "v")
        store.record_feedback("k", success=True)
        node = store.get_node("k")
        assert node.success_count == 1

    def test_tag_then_recall(self):
        store = _make_sa_store()
        store.put("k", "v")
        store.tag("k", frozenset({"hot"}))
        results = store.recall_all(tag="hot")
        assert any(n.key == "k" for n in results)

    def test_causal_chain_persisted(self):
        store = _make_sa_store()
        store.put("parent", "p")
        store.put("child", "c")
        store.link("child", "parent")
        chain = store.recall_chain("child")
        assert len(chain) == 2
        assert chain[0].key == "parent"
        assert chain[1].key == "child"
