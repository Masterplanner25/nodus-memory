# nodus-memory — Design Decision Log (Phase 0)

**Status:** Complete — 2026-05-29
**Decisions:** D1–D10 (all locked)

---

## D1 — No new opcodes

BYTECODE_VERSION stays at 4. nodus-memory adds Python builtins and .nd wrapper functions only.
No new VM instructions, no compiler changes. Verified by the invariant test.

## D2 — Optional database backend

The library must work without any external infrastructure. `InMemoryBackend` is the default and
only required backend. `SQLAlchemyBackend` is gated behind the `[db]` optional extra
(`sqlalchemy>=2.0`). pgvector is deferred to v0.2 and will be an additional `[pgvector]` extra.

**Why:** CI runs without PostgreSQL. Agents in development need memory that works immediately.
Production deployments add the `[db]` extra for persistence.

## D3 — Python ≥3.11

Matches nodus-lang 4.0.0 and nodus-a2a v0.1.0. Uses `from __future__ import annotations` for
forward references. No 3.10 support — frozen dataclasses with `slots=True` and
`tomllib` (stdlib) require 3.11.

## D4 — Minimal required dependencies

Only `nodus-lang>=4.0.0,<5.0.0` is required. All persistence, embedding, and NLP deps are
optional extras:

| Extra | Adds |
|-------|------|
| `[db]` | `sqlalchemy>=2.0` |
| `[embed]` | `numpy>=1.24` |
| `[nltk]` | `nltk>=3.8` |
| `[all]` | All of the above |

**Why:** Importing `nodus_memory` in a nodus script should never fail due to missing infra.
Optional extras are installed by operators who need those capabilities.

## D5 — MAS path format

Memory Address Space paths follow: `/memory/{tenant}/{namespace}/{type}/{key}`

- `tenant`: tenant_id (e.g. "alice", "org-123")
- `namespace`: logical grouping (e.g. "agent", "session", "shared")
- `type`: node type label (e.g. "fact", "event", "plan", "observation")
- `key`: the user-supplied key string (URL-encoded if it contains `/`)

`path_prefix(tenant, namespace)` returns `/memory/{tenant}/{namespace}` for prefix queries.

**Why:** Mirrors the A.I.N.D.Y. MAS design. Hierarchical paths enable range scans across a
tenant's namespace without filtering by tag — important for large memory sets.

## D6 — Pluggable embedding provider; pgvector deferred to v0.2

`EmbeddingProvider` is an ABC with one method: `embed(text: str) → list[float]`. The default
is `NoOpProvider` returning an all-zeros vector. No OpenAI, Cohere, or any external provider
is hardcoded in v0.1.

`recall_similar()` is implemented in v0.1 as a stub: it embeds the query text and computes
cosine similarity against stored node embeddings (in-memory with numpy if available). With
`NoOpProvider`, it always returns an empty list. The pgvector backend (full vector indexing)
is v0.2.

**Why:** Avoids requiring API keys in CI. Providers are user-supplied at construction time,
keeping the library vendor-neutral.

## D7 — Backward-compatible with std:memory

The library exposes the same function names as the built-in `std:memory` (get, put, delete,
has, keys) plus new ones (recall_from, recall_all, share, forget, tag, link).

`std:memory` remains the built-in in-process KV primitive — it is not replaced. `import
"nodus-memory"` adds the extended API on top. Scripts that use `std:memory` keep working
unchanged.

**Why:** Existing Nodus scripts must not break. The library is an additive layer.

## D8 — Tenant isolation enforced in MemoryStore, not language layer

`MemoryStore` accepts a `tenant_id` at construction. Every read/write call validates that the
path's tenant component matches the configured tenant. Cross-tenant access raises `TenantError`.

The `.nd` bindings call into `MemoryStore` via Python builtins — they never receive a raw
backend reference. Tenant enforcement is always in Python, never in Nodus script code.

**Why:** Security boundaries must be in a single, auditable place. Language code is user-
generated; it cannot be trusted to enforce its own tenant isolation.

## D9 — JSON-safe value constraint inherited from nodus-lang

`MemoryNode` values must pass nodus-lang's `is_json_safe()` check (imported from
`nodus.services.memory_runtime`). This ensures values can be serialized to/from the DB backend
and passed through the Nodus VM without marshaling errors.

## D10 — Build backend: hatchling

Consistent with nodus-a2a v0.1.0. Simpler than setuptools for pure-Python packages. The wheel
includes `src/nodus_memory/nd/*.nd` as package data via `artifacts`.
