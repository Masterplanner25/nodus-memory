"""Phase K — end-to-end integration tests."""
from __future__ import annotations

import pytest


class TestTwoRuntimesSharedBackend:
    """Two NodusRuntime instances sharing an SQLAlchemyBackend (SQLite)."""

    @pytest.fixture
    def shared_store(self):
        sa = pytest.importorskip("sqlalchemy")
        from nodus_memory import MemoryStore, MemoryConfig
        return MemoryStore(MemoryConfig(
            tenant_id="alice", backend="sqlalchemy", db_url="sqlite:///:memory:"
        ))

    def test_script_a_writes_script_b_reads(self, shared_store):
        from nodus import NodusRuntime
        from nodus_memory import attach_to_runtime

        rt_a = NodusRuntime()
        attach_to_runtime(rt_a, shared_store)
        r_a = rt_a.run_source('''
import "nodus-memory"
share("cross-agent", "from A")
''')
        assert r_a["ok"], r_a["errors"]

        rt_b = NodusRuntime()
        attach_to_runtime(rt_b, shared_store)
        r_b = rt_b.run_source('''
import "nodus-memory"
let v = recall_from("cross-agent")
print(v)
''')
        assert r_b["ok"], r_b["errors"]
        assert "from A" in r_b["stdout"]

    def test_causal_chain_persisted_across_runtimes(self, shared_store):
        from nodus import NodusRuntime
        from nodus_memory import attach_to_runtime

        # Python API writes the chain (language binding for link not yet exercised here)
        shared_store.put("root", "observation")
        shared_store.put("child", "conclusion")
        shared_store.link("child", "root")

        rt = NodusRuntime()
        attach_to_runtime(rt, shared_store)
        r = rt.run_source('''
import "nodus-memory"
let v = recall_from("child")
print(v)
''')
        assert r["ok"], r["errors"]
        assert "conclusion" in r["stdout"]

        chain = shared_store.recall_chain("child")
        assert len(chain) == 2
        assert chain[0].key == "root"
        assert chain[1].key == "child"

    def test_feedback_survives_runtime_restart(self, shared_store):
        from nodus import NodusRuntime
        from nodus_memory import attach_to_runtime

        shared_store.put("fact", "earth is round")
        shared_store.record_feedback("fact", success=True)
        shared_store.record_feedback("fact", success=True)

        rt = NodusRuntime()
        attach_to_runtime(rt, shared_store)
        r = rt.run_source('''
import "nodus-memory"
let v = recall_from("fact")
print(v)
''')
        assert "earth is round" in r["stdout"]
        node = shared_store.get_node("fact")
        assert node.success_count == 2


class TestInMemoryFullWorkflow:
    def test_store_tag_recall_feedback_chain(self):
        from nodus import NodusRuntime
        from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime

        store = MemoryStore(MemoryConfig(tenant_id="test"))
        store.put("obs1", "sky is blue", tags=frozenset({"observation"}))
        store.put("obs2", "grass is green", tags=frozenset({"observation"}))
        store.put("conclusion", "nature has color", tags=frozenset({"conclusion"}))
        store.link("conclusion", "obs1")
        store.record_feedback("obs1", success=True)
        store.record_feedback("obs2", success=True)

        observations = store.recall_all(tag="observation")
        assert len(observations) == 2

        chain = store.recall_chain("conclusion")
        assert len(chain) == 2
        assert chain[0].key == "obs1"

        rt = NodusRuntime()
        attach_to_runtime(rt, store)
        r = rt.run_source('''
import "nodus-memory"
let v = recall_from("conclusion")
print(v)
''')
        assert "nature has color" in r["stdout"]

    def test_scoring_orders_results(self):
        from nodus_memory import MemoryStore, MemoryConfig

        store = MemoryStore(MemoryConfig(tenant_id="score-test"))
        store.put("popular", "lots of feedback")
        store.put("obscure", "rarely used")
        for _ in range(5):
            store.record_feedback("popular", success=True)

        by_weight = store.recall_all(sort_by="weight")
        keys = [n.key for n in by_weight]
        assert keys.index("popular") < keys.index("obscure")
