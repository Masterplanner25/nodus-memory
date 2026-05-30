"""Phase K — standing invariants (8 assertions that must hold for all of v0.1)."""
from __future__ import annotations

import pytest


class TestBytecodeVersionUnchanged:
    def test_bytecode_version_is_4(self):
        from nodus.compiler.compiler import BYTECODE_VERSION
        assert BYTECODE_VERSION == 4


class TestBackendABCCompliance:
    def test_in_memory_backend_implements_all_abstract_methods(self):
        import inspect
        from nodus_memory.backends.base import MemoryBackend
        from nodus_memory.backends.memory import InMemoryBackend
        abstract = {
            name for name, method in inspect.getmembers(MemoryBackend, predicate=inspect.isfunction)
            if getattr(method, "__isabstractmethod__", False)
        }
        concrete = set(dir(InMemoryBackend))
        missing = abstract - concrete
        assert not missing, f"InMemoryBackend missing: {missing}"

    def test_sqlalchemy_backend_implements_all_abstract_methods(self):
        import inspect
        from nodus_memory.backends.base import MemoryBackend
        from nodus_memory.backends.sqlalchemy import SQLAlchemyBackend
        abstract = {
            name for name, method in inspect.getmembers(MemoryBackend, predicate=inspect.isfunction)
            if getattr(method, "__isabstractmethod__", False)
        }
        concrete = set(dir(SQLAlchemyBackend))
        missing = abstract - concrete
        assert not missing, f"SQLAlchemyBackend missing: {missing}"


class TestTenantIsolationNeverLeaks:
    def test_cross_tenant_recall_all_always_empty(self):
        from nodus_memory import MemoryStore, MemoryConfig
        from nodus_memory.backends.memory import InMemoryBackend
        shared = InMemoryBackend()
        alice = MemoryStore(MemoryConfig(tenant_id="alice"), backend=shared)
        bob = MemoryStore(MemoryConfig(tenant_id="bob"), backend=shared)
        for i in range(5):
            alice.put(f"k{i}", i)
        results = bob.recall_all()
        assert results == [], f"Bob saw Alice's data: {results}"

    def test_cross_tenant_get_returns_none(self):
        from nodus_memory import MemoryStore, MemoryConfig
        from nodus_memory.backends.memory import InMemoryBackend
        shared = InMemoryBackend()
        alice = MemoryStore(MemoryConfig(tenant_id="alice"), backend=shared)
        bob = MemoryStore(MemoryConfig(tenant_id="bob"), backend=shared)
        alice.put("secret", "alice-only")
        assert bob.get("secret") is None


class TestBackendAPIEquivalence:
    """InMemoryBackend and SQLAlchemyBackend must behave identically for core operations."""

    @pytest.fixture(params=["memory", "sqlalchemy"])
    def store(self, request):
        sa = pytest.importorskip("sqlalchemy") if request.param == "sqlalchemy" else None
        from nodus_memory import MemoryStore, MemoryConfig
        if request.param == "sqlalchemy":
            return MemoryStore(MemoryConfig(
                tenant_id="test", backend="sqlalchemy", db_url="sqlite:///:memory:"
            ))
        return MemoryStore(MemoryConfig(tenant_id="test"))

    def test_put_get(self, store):
        store.put("k", "v")
        assert store.get("k") == "v"

    def test_has(self, store):
        store.put("k", "v")
        assert store.has("k")
        assert not store.has("missing")

    def test_delete(self, store):
        store.put("k", "v")
        assert store.delete("k")
        assert store.get("k") is None

    def test_recall_all(self, store):
        store.put("a", 1)
        store.put("b", 2)
        nodes = store.recall_all()
        assert len(nodes) == 2

    def test_tag_and_recall_by_tag(self, store):
        store.put("k", "v")
        store.tag("k", frozenset({"hot"}))
        results = store.recall_all(tag="hot")
        assert any(n.key == "k" for n in results)

    def test_feedback(self, store):
        store.put("k", "v")
        store.record_feedback("k", success=True)
        node = store.get_node("k")
        assert node.success_count == 1


class TestLanguageBindingsSafeImport:
    def test_bindings_do_not_import_backends(self):
        import nodus_memory.nodus_bindings as nb
        src = open(nb.__file__).read()
        assert "from nodus_memory.backends" not in src

    def test_top_level_import_requires_no_database(self):
        # This should succeed even if sqlalchemy is not installed
        import nodus_memory  # noqa: F401


class TestMemoryNodeJSONSafe:
    def test_node_value_is_json_serializable(self):
        import json
        from nodus_memory import MemoryStore, MemoryConfig
        store = MemoryStore(MemoryConfig(tenant_id="t"))
        values = [
            "string",
            42,
            3.14,
            True,
            None,
            [1, 2, 3],
            {"key": "value"},
        ]
        for v in values:
            node = store.put("k", v)
            serialized = json.dumps(node.value)
            assert json.loads(serialized) == v


class TestRecallFromNeverRaisesForMissing:
    def test_recall_from_missing_returns_none(self):
        from nodus_memory import MemoryStore, MemoryConfig
        store = MemoryStore(MemoryConfig(tenant_id="t"))
        assert store.recall_from("nonexistent") is None

    def test_get_missing_returns_none(self):
        from nodus_memory import MemoryStore, MemoryConfig
        store = MemoryStore(MemoryConfig(tenant_id="t"))
        assert store.get("nonexistent") is None
