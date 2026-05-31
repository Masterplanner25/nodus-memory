"""nodus-memory — persistent, searchable, scored agent memory.

Models:
    MemoryNode      — content, tags, path, embedding, scores, feedback counters
    MemoryLink      — directed causal/associative link between nodes
    VALID_NODE_TYPES, VALID_MEMORY_TYPES

Address Space (MAS):
    build_path(tenant, namespace, type, node_id) → str
    parse_path(path) → dict
    glob_match(path, pattern) → bool
    derive_legacy_path(node_id, user_id, memory_type) → str

Scoring:
    MemoryScore     — composite relevance score
    score_nodes()   — rank nodes by semantic + tag + impact + weight
    update_feedback(node, success) → update weight/impact in-place

Embedding:
    EmbeddingProvider  — protocol: embed(texts) + dimensions
    NoopEmbeddingProvider — zero-vector fallback
    OpenAIEmbeddingProvider — requires openai extra

Store:
    MemoryStore        — protocol
    InMemoryStore      — thread-safe dict-backed store (for tests)

Search:
    recall()           — sync retrieval with optional embedder
    recall_async()     — async retrieval (preferred in async contexts)
"""
from .address import build_path, derive_legacy_path, glob_match, parse_path
from .embedding import EmbeddingProvider, NoopEmbeddingProvider, OpenAIEmbeddingProvider
from .models import VALID_MEMORY_TYPES, VALID_NODE_TYPES, MemoryLink, MemoryNode
from .scoring import MemoryScore, score_nodes, update_feedback
from .search import recall, recall_async
from .store import InMemoryStore, MemoryStore

__all__ = [
    # Models
    "MemoryNode",
    "MemoryLink",
    "VALID_NODE_TYPES",
    "VALID_MEMORY_TYPES",
    # Address Space
    "build_path",
    "parse_path",
    "glob_match",
    "derive_legacy_path",
    # Scoring
    "MemoryScore",
    "score_nodes",
    "update_feedback",
    # Embedding
    "EmbeddingProvider",
    "NoopEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    # Store
    "MemoryStore",
    "InMemoryStore",
    # Search
    "recall",
    "recall_async",
]
