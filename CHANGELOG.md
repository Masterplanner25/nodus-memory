# Changelog

Format: [Keep a Changelog](https://keepachangelog.com)
Versioning: [Semantic Versioning](https://semver.org)

## [Unreleased]

## [0.1.0] — PREPARED, NOT RELEASED

> **Coordinated launch:** nodus-memory v0.1.0 is prepared but not published.
> Release waits for the three-artifact set (nodus-lang 4.0.0, nodus-mcp 0.1.0,
> nodus-a2a 0.1.0) to ship first. nodus-memory is a separate, subsequent release.

### Added

**Core library (Phases A–K)**

- `MemoryNode` frozen dataclass — id, tenant_id, namespace, type, key, value, tags,
  path, created_at, updated_at, causal_parent_id, embedding, impact_score, usage_count,
  success_count, failure_count
- `MemoryConfig` dataclass — backend, tenant_id, namespace, db_url, embedding_provider,
  max_recall_limit
- Error hierarchy: `MemoryError`, `KeyNotFoundError`, `TenantError`, `BackendError`,
  `EmbeddingError`, `CausalCycleError`, `InvalidAddressError`
- Memory Address Space (MAS): `build_path()`, `parse_path()`, `validate_path()`,
  `path_prefix()`, `path_prefix_type()`
- `MemoryBackend` ABC with 9 abstract methods
- `InMemoryBackend` — thread-safe, dict-based, default backend
- `SQLAlchemyBackend` — SQLAlchemy Core backend (optional `[db]` extra)
- `MemoryStore` — tenant-enforcing facade over any backend
  - CRUD: `put()`, `get()`, `get_node()`, `delete()`, `has()`, `keys()`
  - Retrieval: `recall_from()`, `recall_all()`, `recall_similar()`, `recall_chain()`, `share()`
  - Tags: `tag()`
  - Causal chain: `link()`, `recall_chain()` with cycle detection
  - Feedback: `record_feedback()`
  - Sort: `sort_by="created_at"` (default) or `"weight"` (ScoreTracker)
- `ScoreTracker` — `compute_weight()`, `record_success()`, `record_failure()`
- `EmbeddingProvider` ABC + `NoOpProvider`
- `cosine_similarity()` — pure-stdlib cosine similarity
- `recall_similar()` stub — functional with real provider; returns empty with NoOpProvider
- Nodus language bindings: `attach_to_runtime(runtime, store)` registers 6 host functions
  - `nm_recall_from`, `nm_share`, `nm_forget`, `nm_recall_all`, `nm_tag`, `nm_link`
- `nd/index.nd` — Nodus wrappers: `recall_from`, `share`, `forget`, `recall_all`, `tag`, `link`
- `nodus.nd` entry-point: `nodus-memory = nodus_memory.nd.nd:get_nd_root`
- CLI: `python -m nodus_memory` — store, recall, list, tag, feedback
- 192 tests, 97% coverage (gate: 80%)
- 5 design docs: 00-decisions (D1–D10), 01-memory-model, 02-backends, 03-retrieval,
  04-language-bindings, 05-deferred

### Design Decisions

- **D1** — No new opcodes; BYTECODE_VERSION stays 4
- **D2** — Optional database backend; InMemoryBackend works without any infra
- **D3** — Python ≥3.11
- **D4** — Only `nodus-lang>=4.0.0,<5.0.0` required; SQLAlchemy, numpy, NLTK are optional extras
- **D5** — MAS path format: `/memory/{tenant}/{namespace}/{type}/{key}`
- **D6** — Pluggable EmbeddingProvider ABC; pgvector deferred to v0.2
- **D7** — Backward-compatible with std:memory (additive layer)
- **D8** — Tenant isolation enforced in MemoryStore, not language layer
- **D9** — JSON-safe value constraint inherited from nodus-lang
- **D10** — Build backend: hatchling

### Deferred to v0.2+

- pgvector / production vector search (requires PostgreSQL + embedding provider)
- NLTK text preprocessing
- Rust native scorer (Maturin)
- Embedding provider integrations (OpenAI, Cohere, local)
- Memory feedback learning loop (adaptive weight updates)
- Multi-namespace cross-agent sharing via Redis pub/sub
