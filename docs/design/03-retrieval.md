# nodus-memory Design Doc 03 — Retrieval Strategies

**Doc:** 03-retrieval.md
**Phase:** 1 (design)
**Status:** Complete — 2026-05-29
**Decisions grounded:** D5, D6
**Covers:** Recall strategies: exact key, tag, path-prefix, vector similarity (v0.2)

---

## Purpose

Defines the four retrieval strategies in v0.1, their API, semantics, and the stub
for vector similarity that ships in v0.1 but becomes functional in v0.2.

---

## A — Strategy 1: Exact Key Lookup

`store.recall_from(key)` / `store.get(key)`

- Constructs the full MAS path: `/memory/{tenant}/{namespace}/{type}/{key}`
- Calls `backend.get(path)`
- Returns `node.value` or `None` (never raises for missing keys — invariant 8)
- Automatically increments `usage_count` by 1 on successful retrieval

`type` defaults to `"general"`. To look up in a different type bucket:
`store.get(key, type="fact")`.

---

## B — Strategy 2: Tag-Based Retrieval

`store.recall_all(tag="important")` / `store.recall_all(tags=frozenset({"a", "b"}))`

- AND semantics: node must have ALL listed tags in its `tags` set
- Calls `backend.recall_by_tag(tags, tenant_prefix)` where `tenant_prefix = /memory/{tenant}/{namespace}`
- Returns list of `MemoryNode`, sorted by `created_at` (default) or `weight` (if `sort_by="weight"`)
- `limit` caps the result count (default: `MemoryConfig.max_recall_limit = 100`)

**Combining tag + path:**
`store.recall_all(tag="hot", path_prefix_override="/memory/alice/session")` — tag filter
applied after path-prefix pre-filter.

---

## C — Strategy 3: Path-Prefix Traversal

`store.recall_all(path_prefix_override="/memory/alice/session/event")`

- Direct prefix scan: backend returns all nodes whose path starts with the prefix
- Useful for: "all events in this session", "all facts in the 'global' namespace"
- Use `address.path_prefix_type(tenant, namespace, type)` to build the prefix
- Tenant isolation enforced: if prefix doesn't start with `/memory/{own_tenant}/`, raises `TenantError`

---

## D — Strategy 4: Vector Similarity (v0.1 stub)

`store.recall_similar(text, top_k=5, threshold=0.7)`

**v0.1 behavior (stub):**
- Calls `embedding_provider.embed(text)` to get a query vector
- If all values in the query vector are `0.0` (i.e., `NoOpProvider`), returns `[]`
- Otherwise: loads all nodes in namespace, computes cosine similarity for nodes that have
  `embedding` set, returns top-k nodes above threshold
- Cosine similarity computed in pure Python (`embedding.cosine_similarity()`)

**v0.2 behavior (planned):**
- pgvector ANN index query (approximate nearest neighbor)
- Async embedding pipeline (embed on `put`, not on `recall_similar`)
- numpy vectorized similarity for speed
- OpenAI / Cohere / local provider integrations

**Why ship the stub in v0.1:** Lets callers write code against the API today; swapping
from `NoOpProvider` to a real provider in v0.2 requires no API changes.

---

## E — Scoring and Sort Order

`recall_all(sort_by="weight")` sorts by `ScoreTracker.compute_weight(node)`:

```
weight = impact_score * (1 + success_ratio) * log1p(usage_count)
```

Default sort: `created_at` (chronological, oldest first).

---

## F — Retrieval API Summary

| Method | Strategy | Returns |
|--------|----------|---------|
| `recall_from(key)` | Exact key | `value \| None` |
| `get(key)` | Exact key | `value \| None` |
| `get_node(key)` | Exact key | `MemoryNode \| None` |
| `recall_all(tag=...)` | Tag filter | `list[MemoryNode]` |
| `recall_all(path_prefix_override=...)` | Path prefix | `list[MemoryNode]` |
| `recall_all()` | All in namespace | `list[MemoryNode]` |
| `recall_chain(key)` | Causal chain walk | `list[MemoryNode]` |
| `recall_similar(text)` | Vector similarity | `list[MemoryNode]` |
