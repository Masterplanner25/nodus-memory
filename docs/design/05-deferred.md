# nodus-memory Design Doc 05 — Deferred Features (v0.2+)

**Doc:** 05-deferred.md
**Phase:** 1 (design)
**Status:** Complete — 2026-05-29
**Decisions grounded:** D2, D4, D6
**Covers:** Features explicitly deferred from v0.1 scope

---

## Purpose

Documents capabilities that were considered during Phase 1 design and explicitly deferred
to v0.2+. Serves as the v0.2 planning seed.

---

## DD-1 — pgvector / Production Vector Search

**v0.1 status:** `recall_similar()` is a stub. With `NoOpProvider`, it always returns
an empty list. With a real `EmbeddingProvider`, it computes cosine similarity in pure
Python against stored embeddings — not suitable for large memory sets.

**v0.2 plan:**
- `[pgvector]` optional extra: `sqlalchemy[asyncio]`, `pgvector`, `asyncpg`
- `PgVectorBackend` extends `SQLAlchemyBackend` with a `vector(1536)` column
- `recall_similar()` delegates to `pgvector` ANN query (`<=>` operator)
- Embedding pipeline: async worker that embeds newly-stored nodes in the background
- Index type: IVFFlat (approximate) with `nlist` configurable

**Reason for deferral:** Requires PostgreSQL + an embedding API key in CI. Not testable
without external infrastructure. The `EmbeddingProvider` ABC and `recall_similar()` stub
ensure API compatibility — no breaking changes in v0.2.

---

## DD-2 — NLTK Text Preprocessing

**v0.1 status:** Not implemented. Memory values are stored as-is.

**v0.2 plan:**
- `[nltk]` optional extra
- `TextPreprocessor`: tokenize → lowercase → stopword removal → stemming
- Automatic preprocessing on `put()` for text values (opt-in via `MemoryConfig`)
- Improved recall_similar accuracy: preprocess query text before embedding

**Reason for deferral:** NLTK corpus downloads add 50MB+ to the environment.
Not in scope for the baseline library.

---

## DD-3 — Rust Native Scorer (Maturin)

**Status: COMPLETE** — delivered as `nodus-native-memory-engine` v0.1.0
(`C:\dev\nodus-native-memory-engine`, `github.com/Masterplanner25/nodus-native-memory-engine`).

`ScoreTracker.compute_weight()` and `cosine_similarity()` in nodus-memory auto-detect
the native engine and route to Rust when it is installed. The engine also provides
`batch_compute_weights`, `argsort_by_weight`, `traverse_chain`, `would_create_cycle`,
`rank_by_similarity`, and `rank_blended`. Pure-Python fallback is always available via
`is_native()` check.

This DD is closed and does not require any further work in nodus-memory v0.2.

---

## DD-4 — Embedding Provider Integrations

**v0.1 status:** `EmbeddingProvider` ABC only; `NoOpProvider` ships.

**v0.2 plan:**
- `OpenAIEmbeddingProvider(api_key=..., model="text-embedding-3-small")`
- `CohereEmbeddingProvider(api_key=..., model="embed-english-v3.0")`
- Local model support via `SentenceTransformerProvider`
- `AsyncEmbeddingProvider` ABC for non-blocking embed calls

**Reason for deferral:** Provider integrations require API keys and external network
access in tests. The ABC contract is established in v0.1; adding providers is additive.

---

## DD-5 — Memory Feedback Learning Loop (Adaptive Weights)

**v0.1 status:** `record_feedback()` increments counters. `compute_weight()` uses a
fixed formula. No adaptive updates to `impact_score`.

**v0.2 plan:**
- Periodic weight recomputation job (APScheduler or background thread)
- Bayesian update to `impact_score` based on accumulated feedback
- Query expansion: nodes with high weight surface in `recall_all()` even without
  exact tag match ("fuzzy recall")
- Memory decay: old nodes without recent usage lose weight over time

**Reason for deferral:** Learning loop is a higher-level feature. The scoring
infrastructure (ScoreTracker, impact_score, usage_count, success/failure counts) is
already in v0.1. Adaptive updates are a policy layer on top.

---

## DD-6 — Multi-Namespace Cross-Agent Sharing

**v0.1 status:** `store.share()` uses the "shared" namespace but there's no broadcast
or subscription mechanism.

**v0.2 plan:**
- `MemoryBus`: pub/sub over Redis (mirroring the A.I.N.D.Y. event bus design)
- Agents subscribe to a namespace; `share()` broadcasts to all subscribers
- Coordinated with `nodus-events` library (separate, companion library)

**Reason for deferral:** Requires Redis dependency; out of scope for the core memory
library. Will be layered on top via `nodus-events` integration.
