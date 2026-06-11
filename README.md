# nodus-memory

**Persistent, searchable, scored agent memory for Nodus AI systems.**

Provides typed memory nodes with MAS (Memory Address Space) hierarchical path
addressing, semantic + tag + impact scoring, embedding support, and sync/async
recall. No required external dependencies — the in-memory store and NoOp
embedder work out of the box.

> **Note:** An earlier version of this repo provided nodus-lang bindings
> (`attach_to_runtime`, `import "nodus-memory"` in `.nd` scripts). That
> implementation is preserved in the git history. The current package is the
> standalone Tier 2 memory library.

> **Status:** v0.1.0 — published on [PyPI](https://pypi.org/project/nodus-memory/).

---

## Install

```bash
pip install nodus-memory

# With pgvector + SQLAlchemy backend:
pip install "nodus-memory[pgvector]"

# With OpenAI embeddings:
pip install "nodus-memory[openai]"
```

---

## What it provides

| Component | Purpose |
|---|---|
| `MemoryNode` | Content node with tags, path, embedding, scores, feedback |
| `MemoryLink` | Directed causal/associative link between nodes |
| `build_path` / `parse_path` / `glob_match` | MAS hierarchical addressing |
| `score_nodes` / `update_feedback` | Composite relevance scoring |
| `EmbeddingProvider` / `NoopEmbeddingProvider` | Embedding protocol + fallback |
| `InMemoryStore` | Thread-safe in-process store (dev + tests) |
| `recall` / `recall_async` | Sync and async retrieval with optional embedder |

---

## Quick start

```python
from nodus_memory import MemoryNode, InMemoryStore, recall

store = InMemoryStore()

node = MemoryNode(
    content="The capital of France is Paris.",
    tags=["geography", "europe"],
    path="/tenant/alice/fact/paris-capital",
)
store.put(node)

results = recall(query="France capital", store=store, limit=5)
for r in results:
    print(r.node.content, r.score.total)
```

---

## MemoryNode

```python
from nodus_memory import MemoryNode, VALID_NODE_TYPES, VALID_MEMORY_TYPES

node = MemoryNode(
    content="Important fact",
    tags=["fact", "geography"],
    path="/tenant/alice/fact/paris",    # MAS path
    node_type="fact",                   # from VALID_NODE_TYPES
    memory_type="semantic",             # from VALID_MEMORY_TYPES
    embedding=[0.1, 0.2, ...],          # optional float list
)
node.id            # UUID str (auto-generated)
node.created_at    # datetime UTC
node.weight        # float 0.0–1.0 (scoring weight)
node.impact_score  # float (feedback-driven)
```

---

## MAS path addressing

```python
from nodus_memory import build_path, parse_path, glob_match

path = build_path(tenant="alice", namespace="work", type="fact", node_id="paris")
# "/alice/work/fact/paris"

parsed = parse_path(path)
# {"tenant": "alice", "namespace": "work", "type": "fact", "node_id": "paris"}

glob_match("/alice/work/fact/paris", "/alice/work/**")   # True
glob_match("/alice/work/fact/paris", "/alice/home/**")   # False
```

---

## Scoring and feedback

```python
from nodus_memory import score_nodes, update_feedback, MemoryScore

nodes = store.list_all()
query_embedding = embedder.embed(["capital city"])
scored = score_nodes(nodes, query_embedding=query_embedding, query_tags=["geography"])

for result in scored:
    print(result.node.content, result.score.total)
    # result.score.semantic, .tag, .impact, .weight, .recency

# Record outcome to adjust future scores
update_feedback(node, success=True)    # increases weight + impact
update_feedback(node, success=False)   # decreases weight
```

---

## Embedding

```python
from nodus_memory import EmbeddingProvider, NoopEmbeddingProvider

# Zero-vector fallback — no embedding dep needed
embedder = NoopEmbeddingProvider()

# OpenAI (requires nodus-memory[openai])
from nodus_memory import OpenAIEmbeddingProvider
embedder = OpenAIEmbeddingProvider(api_key="sk-...", model="text-embedding-3-small")

# Custom embedder — implement the protocol
class MyEmbedder:
    dimensions = 768
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

---

## Recall

```python
from nodus_memory import recall, recall_async

# Sync
results = recall(
    query="capital of France",
    store=store,
    embedder=embedder,    # optional
    tags=["geography"],   # optional tag filter
    limit=10,
)

# Async
results = await recall_async(query="...", store=store, embedder=embedder)
```

---

## Design

- **No required dependencies.** Core models, MAS, scoring, and in-memory store
  are pure stdlib. Embedding providers and pgvector are optional extras.
- **Protocol-based store.** Any class satisfying `MemoryStore` (put, get, list,
  delete) works as a backend.
- **Thread-safe.** `InMemoryStore` uses `threading.Lock`.
- **Auto-detects nodus-native-memory-engine.** When installed, hot-path scoring
  operations use the Rust extension automatically.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

---

## License

MIT — see [LICENSE](LICENSE).
