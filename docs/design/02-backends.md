# nodus-memory Design Doc 02 — Backend Architecture

**Doc:** 02-backends.md
**Phase:** 1 (design)
**Status:** Complete — 2026-05-29
**Decisions grounded:** D2, D4, D10
**Covers:** MemoryBackend ABC, InMemoryBackend, SQLAlchemyBackend, optional extras strategy

---

## Purpose

Defines the abstraction layer between `MemoryStore` and persistence backends.
Covers how optional extras work, how the two v0.1 backends are structured,
and what the contract is for adding new backends in v0.2+.

---

## A — MemoryBackend ABC

All backends implement `nodus_memory.backends.base.MemoryBackend`:

| Method | Signature | Contract |
|--------|-----------|----------|
| `put` | `(node: MemoryNode) → MemoryNode` | Store or replace; return the stored node |
| `get` | `(path: str) → MemoryNode \| None` | Return node or None if absent |
| `delete` | `(path: str) → bool` | Remove; return True if existed |
| `has` | `(path: str) → bool` | Return True if node exists at path |
| `keys` | `(tenant_prefix: str) → list[str]` | All keys under prefix |
| `recall_by_tag` | `(tags: frozenset[str], tenant_prefix: str) → list[MemoryNode]` | AND-match |
| `recall_by_path` | `(path_prefix: str, limit: int) → list[MemoryNode]` | Prefix scan |
| `recall_all` | `(tenant_prefix: str, limit: int) → list[MemoryNode]` | All under prefix |
| `update` | `(path: str, **fields) → MemoryNode \| None` | Mutate specific fields |

The `MemoryStore` **never** bypasses the ABC — it only calls ABC methods. This ensures
backend swappability. The invariant test verifies both v0.1 backends implement all abstract
methods.

---

## B — InMemoryBackend (default)

**Location:** `nodus_memory.backends.memory`
**No optional extras required.**

Implementation details:
- Thread-safe via `threading.RLock` (one lock per instance)
- Internal storage: `dict[str, MemoryNode]` keyed by full MAS path
- `len(backend)` returns number of stored nodes (for testing)
- All mutations replace the full `MemoryNode` (frozen dataclass semantics)

This backend is the default when no backend is specified. It requires no
external process and works anywhere Python runs. Data does not survive process
restart.

---

## C — SQLAlchemyBackend (optional `[db]` extra)

**Location:** `nodus_memory.backends.sqlalchemy`
**Requires:** `pip install "nodus-memory[db]"` → `sqlalchemy>=2.0`

Database schema (two tables, created on first use):

**`nodus_memory_nodes`**
| Column | Type | Notes |
|--------|------|-------|
| path | VARCHAR(512) PK | MAS path |
| id | VARCHAR(36) | UUID4 |
| tenant_id | VARCHAR(255) | |
| namespace | VARCHAR(255) | |
| type | VARCHAR(255) | |
| key | VARCHAR(512) | |
| value_json | TEXT | JSON-encoded value |
| tags_json | TEXT | JSON-encoded sorted list of tags |
| created_at | FLOAT | Unix timestamp |
| updated_at | FLOAT | Unix timestamp |
| causal_parent_id | VARCHAR(36) nullable | |
| embedding_json | TEXT nullable | JSON-encoded float list |
| impact_score | FLOAT | default 1.0 |
| usage_count | INTEGER | default 0 |
| success_count | INTEGER | default 0 |
| failure_count | INTEGER | default 0 |

**Design choices:**
- SQLAlchemy Core (not ORM) — no declarative base, no session management complexity
- Tags stored inline as `tags_json` (sorted list), not a separate table — avoids join
  complexity for in-memory tag filtering; pgvector backend (v0.2) will have a proper tags table
- `MetaData.create_all()` is called in `__init__`; idempotent (checks existence)
- `update()` uses read-modify-write via `put()` — not atomic under concurrent writers;
  acceptable for v0.1 (production deployments should use a connection pool + row-level locking)

**Connection URL:** passed directly as `db_url` in `MemoryConfig`. Supports any SQLAlchemy
connection string: `sqlite:///:memory:`, `postgresql://user:pw@host/db`, etc.

---

## D — Optional Extras Strategy

```
nodus-memory              → InMemoryBackend only
nodus-memory[db]          → + SQLAlchemyBackend (sqlalchemy>=2.0)
nodus-memory[embed]       → + cosine similarity in recall_similar (numpy>=1.24)
nodus-memory[nltk]        → + text preprocessing (nltk>=3.8) — v0.2 feature
nodus-memory[all]         → all of the above
```

**Import guard pattern** (used in `backends/sqlalchemy.py`):
```python
try:
    import sqlalchemy as sa
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

def _require_sqlalchemy():
    if not _SA_AVAILABLE:
        raise BackendError("sqlalchemy is required — pip install 'nodus-memory[db]'")
```

This defers the import error to first use, so `import nodus_memory` never fails.

---

## E — Bytecode Impact

None. All backend code is pure Python I/O. BYTECODE_VERSION remains 4. (Decision D1)
