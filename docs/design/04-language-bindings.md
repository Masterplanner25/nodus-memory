# nodus-memory Design Doc 04 — Nodus Language Bindings

**Doc:** 04-language-bindings.md
**Phase:** 1 (design)
**Status:** Complete — 2026-05-29
**Decisions grounded:** D1, D7, D8
**Covers:** .nd API surface, backward-compat with std:memory, attach_to_runtime

---

## Purpose

Defines how Nodus scripts access the memory library via `import "nodus-memory"` and
`attach_to_runtime()`. Covers the binding architecture, host function naming, and
backward-compatibility with the built-in `std:memory`.

---

## A — Binding Architecture

The library ships as two layers:

1. **Python layer** (`nodus_bindings.py`): `attach_to_runtime(runtime, store)` registers
   6 host functions on the `NodusRuntime` using `runtime.register_function()`.

2. **Nodus layer** (`nd/index.nd`): Thin `fn` wrappers that call the host functions.
   Imported via `import "nodus-memory"` once the entry-point is resolved.

The `nd/index.nd` is resolved by the Nodus module loader through the `nodus.nd` entry-point
group. The entry-point for `nodus-memory` is:
```
nodus-memory = nodus_memory.nd.nd:get_nd_root
```
Which returns the path to the `nd/` directory. The loader finds `index.nd` inside it.

---

## B — Host Function Names

Host functions use the `nm_` prefix to avoid colliding with nodus-lang built-ins:

| Host function | Arity | Behavior |
|---------------|-------|----------|
| `nm_recall_from` | 1 | `store.get(key)` → value or `None` |
| `nm_share` | 2 | `store.put(key, value)` → `None` |
| `nm_forget` | 1 | `store.delete(key)` → `bool` |
| `nm_recall_all` | 1 | `store.recall_all(tag=tag or None)` → list of values |
| `nm_tag` | 2 | `store.tag(key, frozenset(tags_list))` → `None` |
| `nm_link` | 2 | `store.link(child, parent)` → `None` |

---

## C — Nodus Function API (index.nd)

After `import "nodus-memory"`, scripts have access to:

| Function | Signature | Description |
|----------|-----------|-------------|
| `recall_from(key)` | `(str) → value \| nil` | Retrieve stored value |
| `share(key, value)` | `(str, any) → nil` | Persist a value |
| `forget(key)` | `(str) → bool` | Delete; returns true if existed |
| `recall_all(tag)` | `(str) → list` | Retrieve all values matching tag |
| `tag(key, tags)` | `(str, list) → nil` | Apply tags to a key |
| `link(child, parent)` | `(str, str) → nil` | Set causal parent |

**Important Nodus language notes (from CLAUDE.md):**
- Wrappers use `return expr` explicitly — Nodus doesn't implicitly return the
  last expression result when the last statement is a host function call
- `fn` is a reserved keyword — cannot be used as parameter name
- `print()` is single-argument

---

## D — Language-Level `share` vs Python `store.share()`

At the Nodus language level, `share(key, value)` stores in the **default namespace**
(same as `recall_from`) — so retrieved with `recall_from(key)`. This is the
intuitive script-level behavior.

At the Python level, `store.share(key, value)` stores in the `"shared"` namespace
(explicitly cross-agent). Python callers use `store.share()` for cross-namespace
sharing. Nodus callers use `share()` for simple persistence and `recall_from()` to
retrieve it.

---

## E — Backward Compatibility with std:memory

`std:memory` is the built-in in-process KV primitive. `nodus-memory` is an
**additive** library. Existing scripts using `std:memory` are unaffected.

The language-level API (`recall_from`, `share`, `forget`) uses different names from
`std:memory` (`get`, `put`, `delete`) deliberately — they are complementary, not
competing. A script can use both:

```nodus
import "std:memory"          // built-in KV (script-lifetime only)
import "nodus-memory"        // persistent, searchable, tagged

put("temp", "in-flight")     // std:memory
share("durable", "persisted") // nodus-memory
```

---

## F — Attach Pattern

```python
from nodus import NodusRuntime
from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime

store = MemoryStore(MemoryConfig(tenant_id="my-agent"))
runtime = NodusRuntime()
attach_to_runtime(runtime, store)

# Now scripts can use import "nodus-memory"
runtime.run_file("agent.nd")
```

**One runtime, one store.** If multiple agents share a runtime, they share the store.
For per-agent isolation: create one `MemoryStore` per tenant and one `NodusRuntime`
per agent, or use namespace separation within one store.

---

## G — Bytecode Impact

None. `register_function()` adds entries to `runtime._host_functions` dict.
The VM dispatches host functions via `BuiltinInfo` — same path as all other builtins.
No new opcodes, no compiler changes. BYTECODE_VERSION remains 4. (Decision D1)
