"""Phase I: Nodus language bindings — import 'nodus-memory', recall_from, share, forget."""
from __future__ import annotations

import pytest


def _runtime_with_store(tenant="alice"):
    from nodus import NodusRuntime
    from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime
    store = MemoryStore(MemoryConfig(tenant_id=tenant))
    runtime = NodusRuntime()
    attach_to_runtime(runtime, store)
    return runtime, store


class TestAttachToRuntime:
    def test_attaches_without_error(self):
        from nodus import NodusRuntime
        from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime
        store = MemoryStore(MemoryConfig(tenant_id="t"))
        runtime = NodusRuntime()
        attach_to_runtime(runtime, store)

    def test_nm_functions_callable_directly(self):
        runtime, store = _runtime_with_store()
        result = runtime.run_source('let v = nm_recall_from("k")\nprint(v)')
        assert result["ok"]
        assert "nil" in result["stdout"]

    def test_six_functions_registered(self):
        from nodus import NodusRuntime
        from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime
        store = MemoryStore(MemoryConfig(tenant_id="t"))
        runtime = NodusRuntime()
        attach_to_runtime(runtime, store)
        funcs = ["nm_recall_from", "nm_share", "nm_forget",
                 "nm_recall_all", "nm_tag", "nm_link"]
        for fn_name in funcs:
            assert fn_name in runtime._host_functions, f"{fn_name} not registered"


class TestNodusLanguageBindings:
    def test_import_nodus_memory_succeeds(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('import "nodus-memory"\nprint("loaded")')
        assert result["ok"], result["errors"]
        assert "loaded" in result["stdout"]

    def test_share_and_recall_from(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
share("k", "hello")
let v = recall_from("k")
print(v)
''')
        assert result["ok"], result["errors"]
        assert "hello" in result["stdout"]

    def test_recall_from_missing_returns_nil(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
let v = recall_from("nonexistent")
print(v)
''')
        assert result["ok"], result["errors"]
        assert "nil" in result["stdout"]

    def test_forget_removes_value(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
share("k", "val")
forget("k")
let v2 = recall_from("k")
print(v2)
''')
        assert result["ok"], result["errors"]
        assert "nil" in result["stdout"]

    def test_forget_returns_bool(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
share("k", "v")
let existed = forget("k")
print(existed)
''')
        assert result["ok"], result["errors"]
        assert "true" in result["stdout"]

    def test_recall_all_returns_list(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
share("a", "alpha")
share("b", "beta")
let vals = recall_all("")
print(len(vals))
''')
        assert result["ok"], result["errors"]
        count = int(result["stdout"].strip())
        assert count >= 2

    def test_store_persists_across_run_source_calls(self):
        runtime, _ = _runtime_with_store()
        r1 = runtime.run_source('import "nodus-memory"\nshare("persist", "yes")')
        assert r1["ok"], r1["errors"]
        r2 = runtime.run_source('import "nodus-memory"\nlet v = recall_from("persist")\nprint(v)')
        assert r2["ok"], r2["errors"]
        assert "yes" in r2["stdout"]

    def test_version_accessible(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
print(_version)
''')
        assert result["ok"], result["errors"]
        assert "0.1.0" in result["stdout"]

    def test_numeric_value_round_trips(self):
        runtime, _ = _runtime_with_store()
        result = runtime.run_source('''
import "nodus-memory"
share("num", 42i)
let v = recall_from("num")
print(v)
''')
        assert result["ok"], result["errors"]
        assert "42" in result["stdout"]

    def test_bindings_dont_import_backends_directly(self):
        import nodus_memory.nodus_bindings as nb
        src = open(nb.__file__).read()
        assert "from nodus_memory.backends" not in src
        assert "import nodus_memory.backends" not in src
