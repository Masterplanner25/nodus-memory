"""Phase C: InMemoryBackend CRUD and MemoryStore tenant isolation."""
from __future__ import annotations

import threading
import pytest


def _make_store(tenant="alice", namespace="agent"):
    from nodus_memory.config import MemoryConfig
    from nodus_memory.store import MemoryStore
    return MemoryStore(MemoryConfig(tenant_id=tenant, namespace=namespace))


class TestInMemoryBackend:
    def _backend(self):
        from nodus_memory.backends.memory import InMemoryBackend
        return InMemoryBackend()

    def _node(self, key="k", value="v", tenant="t", ns="n", type="general"):
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        return MemoryNode.create(
            tenant_id=tenant, namespace=ns, key=key, value=value,
            path=build_path(tenant, ns, type, key), type=type
        )

    def test_put_and_get(self):
        b = self._backend()
        node = self._node()
        b.put(node)
        got = b.get(node.path)
        assert got is not None
        assert got.key == "k"

    def test_get_missing_returns_none(self):
        b = self._backend()
        assert b.get("/memory/x/y/z/missing") is None

    def test_has_true(self):
        b = self._backend()
        node = self._node()
        b.put(node)
        assert b.has(node.path)

    def test_has_false(self):
        b = self._backend()
        assert not b.has("/memory/x/y/z/no")

    def test_delete_returns_true(self):
        b = self._backend()
        node = self._node()
        b.put(node)
        assert b.delete(node.path)

    def test_delete_returns_false_when_absent(self):
        b = self._backend()
        assert not b.delete("/memory/x/y/z/no")

    def test_delete_removes_node(self):
        b = self._backend()
        node = self._node()
        b.put(node)
        b.delete(node.path)
        assert b.get(node.path) is None

    def test_keys_lists_all_under_prefix(self):
        b = self._backend()
        for k in ("a", "b", "c"):
            b.put(self._node(key=k))
        keys = b.keys("/memory/t/n")
        assert set(keys) == {"a", "b", "c"}

    def test_keys_does_not_leak_other_tenants(self):
        b = self._backend()
        b.put(self._node(key="alice-key", tenant="alice"))
        b.put(self._node(key="bob-key", tenant="bob"))
        alice_keys = b.keys("/memory/alice/n")
        bob_keys = b.keys("/memory/bob/n")
        assert "bob-key" not in alice_keys
        assert "alice-key" not in bob_keys

    def test_update_mutable_fields(self):
        b = self._backend()
        node = self._node()
        b.put(node)
        updated = b.update(node.path, usage_count=5)
        assert updated is not None
        assert updated.usage_count == 5

    def test_update_missing_returns_none(self):
        b = self._backend()
        result = b.update("/memory/x/y/z/no", usage_count=1)
        assert result is None

    def test_put_overwrites_existing(self):
        b = self._backend()
        n1 = self._node(value="v1")
        n2 = self._node(value="v2")
        b.put(n1)
        b.put(n2)
        got = b.get(n2.path)
        assert got.value == "v2"

    def test_concurrent_puts_are_safe(self):
        b = self._backend()
        errors = []

        def writer(i):
            try:
                b.put(self._node(key=f"key-{i}", tenant="t", ns="n"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(b) == 50


class TestMemoryStoreCRUD:
    def test_put_and_get(self):
        store = _make_store()
        store.put("greeting", "hello")
        assert store.get("greeting") == "hello"

    def test_get_missing_returns_none(self):
        store = _make_store()
        assert store.get("nonexistent") is None

    def test_has_true(self):
        store = _make_store()
        store.put("x", 1)
        assert store.has("x")

    def test_has_false(self):
        store = _make_store()
        assert not store.has("not-there")

    def test_delete_returns_true(self):
        store = _make_store()
        store.put("to-del", "v")
        assert store.delete("to-del")

    def test_delete_returns_false_when_absent(self):
        store = _make_store()
        assert not store.delete("not-there")

    def test_delete_removes_value(self):
        store = _make_store()
        store.put("k", "v")
        store.delete("k")
        assert store.get("k") is None

    def test_keys_lists_stored_keys(self):
        store = _make_store()
        for k in ("a", "b", "c"):
            store.put(k, k)
        assert set(store.keys()) == {"a", "b", "c"}

    def test_get_increments_usage_count(self):
        store = _make_store()
        store.put("k", "v")
        store.get("k")
        store.get("k")
        node = store.get_node("k")
        assert node is not None
        assert node.usage_count == 2


class TestMemoryStoreTenantIsolation:
    def test_alice_cannot_see_bobs_keys(self):
        from nodus_memory.backends.memory import InMemoryBackend
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        shared_backend = InMemoryBackend()
        alice = MemoryStore(MemoryConfig(tenant_id="alice"), backend=shared_backend)
        bob = MemoryStore(MemoryConfig(tenant_id="bob"), backend=shared_backend)

        alice.put("secret", "alice-value")
        bob.put("secret", "bob-value")

        assert alice.get("secret") == "alice-value"
        assert bob.get("secret") == "bob-value"

    def test_alice_cannot_list_bobs_keys(self):
        from nodus_memory.backends.memory import InMemoryBackend
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        shared_backend = InMemoryBackend()
        alice = MemoryStore(MemoryConfig(tenant_id="alice"), backend=shared_backend)
        bob = MemoryStore(MemoryConfig(tenant_id="bob"), backend=shared_backend)

        alice.put("alice-key", "a")
        bob.put("bob-key", "b")

        alice_keys = alice.keys()
        assert "bob-key" not in alice_keys

    def test_cross_tenant_recall_all_returns_empty(self):
        from nodus_memory.backends.memory import InMemoryBackend
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        shared_backend = InMemoryBackend()
        alice = MemoryStore(MemoryConfig(tenant_id="alice"), backend=shared_backend)
        bob = MemoryStore(MemoryConfig(tenant_id="bob"), backend=shared_backend)

        alice.put("k", "v")
        results = bob.recall_all()
        keys = [n.key for n in results]
        assert "k" not in keys

    def test_cross_tenant_prefix_raises_tenant_error(self):
        from nodus_memory.errors import TenantError
        store = _make_store(tenant="alice")
        with pytest.raises(TenantError):
            store.recall_all(path_prefix_override="/memory/bob/agent")

    def test_share_uses_shared_namespace(self):
        store = _make_store()
        store.share("public-key", "shared-value")
        node = store.get_node("public-key", namespace="shared")
        assert node is not None
        assert node.namespace == "shared"
