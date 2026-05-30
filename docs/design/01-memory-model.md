# nodus-memory Design Doc 01 — Memory Model

**Doc:** 01-memory-model.md
**Phase:** 1 (design)
**Status:** Complete — 2026-05-29
**Decisions grounded:** D5, D7, D9
**Covers:** MemoryNode schema, MAS address format, tags, causal links, scoring fields

---

## Purpose

Defines the core data structure (`MemoryNode`), the Memory Address Space (MAS) path format,
and the scoring fields that enable ranked retrieval and feedback loops. This is the shape that
all backends (in-memory, SQLAlchemy, pgvector) must store and return.

---

## A — MemoryNode Schema

### A.1 Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID4, generated at creation |
| `tenant_id` | `str` | Owning tenant; enforced by MemoryStore |
| `namespace` | `str` | Logical grouping within the tenant |
| `type` | `str` | Node type label (e.g. "fact", "event", "plan") |
| `key` | `str` | User-supplied identifier; unique within (tenant, namespace, type) |
| `value` | `object` | JSON-safe value; any type passing `is_json_safe()` |
| `tags` | `frozenset[str]` | Zero or more tags for category-based retrieval |
| `path` | `str` | Derived MAS path: `/memory/{tenant}/{namespace}/{type}/{key}` |
| `created_at` | `float` | Unix timestamp (UTC) at node creation |
| `updated_at` | `float` | Unix timestamp (UTC) at last modification |
| `causal_parent_id` | `str \| None` | ID of the parent node in a causal chain |
| `embedding` | `list[float] \| None` | Vector embedding; `None` until embedded |
| `impact_score` | `float` | Operator-assigned importance weight (default 1.0) |
| `usage_count` | `int` | Number of times this node was retrieved |
| `success_count` | `int` | Feedback: number of marked-success retrievals |
| `failure_count` | `int` | Feedback: number of marked-failure retrievals |

### A.2 Constraints

- `MemoryNode` is a **frozen dataclass** — immutable after creation.
- Updates (tag addition, scoring) produce a new `MemoryNode` via `dataclasses.replace()`.
- `value` must pass `is_json_safe()` from `nodus.services.memory_runtime`.
- `key` must be a non-empty string; it may not contain `/` (use URL encoding if needed).
- `(tenant_id, namespace, type, key)` is the natural unique key — backends enforce this.

### A.3 Default type

When callers omit `type`, the default is `"general"`. The type label is user-chosen and
carries no built-in semantics — it is purely for retrieval filtering and path hierarchy.

---

## B — Memory Address Space (MAS) Path Format

### B.1 Structure

```
/memory/{tenant}/{namespace}/{type}/{key}
```

Examples:
```
/memory/alice/agent/fact/project-deadline
/memory/org-123/session/event/login-2026-05-29T14:32Z
/memory/default/shared/plan/weekly-review
```

### B.2 Functions (address.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_path` | `(tenant, namespace, type, key) → str` | Construct a canonical path |
| `parse_path` | `(path) → dict` | Decompose into `{tenant, namespace, type, key}` |
| `validate_path` | `(path) → None` | Raise `InvalidAddressError` if malformed |
| `path_prefix` | `(tenant, namespace) → str` | Prefix for namespace-level range queries |
| `path_prefix_type` | `(tenant, namespace, type) → str` | Prefix for type-level range queries |

### B.3 Validation rules

A path is valid if:
- Starts with `/memory/`
- Has exactly 4 additional non-empty segments separated by `/`
- No segment is empty or contains only whitespace

`InvalidAddressError` is raised for any violation.

---

## C — Tags

Tags are a `frozenset[str]` on each node. They are:
- Set at creation (optional; default empty)
- Replaced on update via `MemoryStore.tag(key, new_tags)`
- Queried via `recall_by_tag(tags)` — AND semantics (node must have ALL listed tags)
- Case-sensitive strings; no normalization applied by the library

Tags are stored as a separate `memory_tags` table in SQLAlchemyBackend
(one row per tag per node) to enable indexed lookups.

---

## D — Causal Chain

`causal_parent_id` links a node to its logical predecessor in a reasoning chain. This enables
agents to reconstruct the sequence of observations/conclusions that led to a given memory.

- `link(child_key, parent_key)` sets `causal_parent_id` on `child_key` to the ID of the node
  at `parent_key`. Both keys must exist in the same (tenant, namespace).
- `recall_chain(key, max_depth=10)` walks the chain from `key` toward the root, returning
  nodes in order from oldest ancestor to the given node.
- Cycle detection: if walking the chain would revisit a node already seen, `CausalCycleError`
  is raised before the cycle is traversed.

---

## E — Scoring Fields

### E.1 Purpose

Scoring enables ranked retrieval: nodes with higher weight surface first in `recall_all()`
results when the caller passes `sort_by="weight"`.

### E.2 Weight formula (ScoreTracker.compute_weight)

```
weight = impact_score * (1 + success_ratio) * log1p(usage_count)
```

Where:
- `success_ratio = success_count / (success_count + failure_count)` (0.0 if no feedback)
- `log1p(usage_count)` rewards frequently-accessed nodes without allowing it to dominate

This formula is intentionally simple. A more sophisticated learning loop is deferred to v0.2.

### E.3 Feedback API

- `record_feedback(key, success=True)` increments `success_count` and `usage_count`
- `record_feedback(key, success=False)` increments `failure_count` and `usage_count`
- Retrieving a node via `recall_from()` automatically increments `usage_count` by 1 (no
  success/failure signal — that requires an explicit `record_feedback()` call)

---

## F — Bytecode Impact

None. `MemoryNode` is a pure Python dataclass. MAS addressing is pure string manipulation.
Scoring is pure arithmetic. BYTECODE_VERSION remains 4. (Decision D1)
