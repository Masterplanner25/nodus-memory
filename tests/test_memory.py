"""nodus-memory tests — all run without external services using InMemoryStore."""
import asyncio
import pytest

from nodus_memory import (
    InMemoryStore, MemoryLink, MemoryNode, MemoryScore,
    NoopEmbeddingProvider,
    build_path, derive_legacy_path, glob_match, parse_path,
    recall, recall_async, score_nodes, update_feedback,
)


def _node(user_id="u1", content="test content", tags=None, **kwargs):
    return MemoryNode(
        content=content,
        tags=tags or [],
        user_id=user_id,
        **kwargs,
    )


# ── MemoryNode ────────────────────────────────────────────────────────────────

def test_node_defaults():
    n = _node()
    assert n.id
    assert n.weight == 1.0
    assert n.impact_score == 0.0
    assert n.embedding is None


def test_node_touch_updates_updated_at():
    import time
    n = _node()
    before = n.updated_at
    time.sleep(0.01)
    n.touch()
    assert n.updated_at > before


# ── MAS address helpers ───────────────────────────────────────────────────────

def test_build_path_with_node_id():
    p = build_path("user-1", "entities", "updated", "node-abc")
    assert p == "/memory/user-1/entities/updated/node-abc"


def test_build_path_directory():
    p = build_path("user-1", "entities", "updated")
    assert p == "/memory/user-1/entities/updated"


def test_parse_path_full():
    result = parse_path("/memory/user-1/entities/updated/abc")
    assert result["tenant_id"] == "user-1"
    assert result["namespace"] == "entities"
    assert result["addr_type"] == "updated"
    assert result["node_id"] == "abc"


def test_parse_path_invalid():
    assert parse_path("not/a/path") == {}
    assert parse_path("") == {}


def test_glob_match_single_wildcard():
    assert glob_match("/memory/u1/ent/updated/abc", "/memory/u1/ent/*") is True
    assert glob_match("/memory/u1/ent/updated/abc", "/memory/u2/ent/*") is False


def test_glob_match_double_wildcard():
    assert glob_match("/memory/u1/ent/updated/abc", "/memory/u1/**") is True


def test_glob_match_exact():
    p = "/memory/u1/ent/updated/abc"
    assert glob_match(p, p) is True
    assert glob_match(p, p + "x") is False


def test_derive_legacy_path():
    p = derive_legacy_path("node-1", "user-1", "insight")
    assert "user-1" in p
    assert "_legacy" in p
    assert "node-1" in p


# ── Scoring ───────────────────────────────────────────────────────────────────

def test_score_nodes_empty():
    assert score_nodes([]) == []


def test_score_nodes_tag_overlap():
    n1 = _node(tags=["a", "b"])
    n2 = _node(tags=["c"])
    results = score_nodes([n1, n2], query_tags=["a", "b"])
    # n1 has higher tag overlap
    assert results[0][0] is n1


def test_score_nodes_returns_sorted_descending():
    nodes = [_node(impact_score=0.1), _node(impact_score=0.9)]
    results = score_nodes(nodes)
    assert results[0][1].total >= results[1][1].total


def test_update_feedback_success():
    n = _node()
    update_feedback(n, success=True)
    assert n.success_count == 1
    assert n.weight > 1.0


def test_update_feedback_failure():
    n = _node()
    update_feedback(n, success=False)
    assert n.failure_count == 1
    assert n.weight < 1.0


def test_impact_score_reflects_ratio():
    n = _node()
    update_feedback(n, success=True)
    update_feedback(n, success=True)
    update_feedback(n, success=False)
    assert 0.5 < n.impact_score <= 1.0


# ── InMemoryStore ─────────────────────────────────────────────────────────────

def test_store_write_and_get():
    store = InMemoryStore()
    n = _node()
    store.write(n)
    found = store.get(n.id, "u1")
    assert found is n


def test_store_get_wrong_user_returns_none():
    store = InMemoryStore()
    n = _node(user_id="u1")
    store.write(n)
    assert store.get(n.id, "u2") is None


def test_store_search_by_tags():
    store = InMemoryStore()
    n1 = _node(tags=["auth", "login"])
    n2 = _node(tags=["data"])
    store.write(n1); store.write(n2)
    results = store.search_by_tags(["auth"], "u1", 10)
    assert n1 in results
    assert n2 not in results


def test_store_search_by_path():
    store = InMemoryStore()
    n = _node(path="/memory/u1/ent/updated/abc")
    store.write(n)
    results = store.search_by_path("/memory/u1/ent/*", "u1", 10)
    assert n in results


def test_store_delete():
    store = InMemoryStore()
    n = _node()
    store.write(n)
    assert store.delete(n.id, "u1") is True
    assert store.get(n.id, "u1") is None


def test_store_list_by_user():
    store = InMemoryStore()
    store.write(_node(user_id="u1"))
    store.write(_node(user_id="u1"))
    store.write(_node(user_id="u2"))
    assert len(store.list_by_user("u1")) == 2
    assert len(store.list_by_user("u2")) == 1


def test_store_update_feedback():
    store = InMemoryStore()
    n = _node()
    store.write(n)
    store.update_feedback(n.id, success=True)
    updated = store.get(n.id, "u1")
    assert updated.success_count == 1


# ── recall ────────────────────────────────────────────────────────────────────

def test_recall_by_tags():
    store = InMemoryStore()
    n = _node(tags=["important"], content="auth decision")
    store.write(n)
    results = recall("auth", "u1", store, tags=["important"])
    assert n in results


def test_recall_empty_store():
    results = recall("query", "u1", InMemoryStore())
    assert results == []


def test_recall_limit():
    store = InMemoryStore()
    for _ in range(10):
        store.write(_node(tags=["x"]))
    results = recall("x", "u1", store, tags=["x"], limit=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_recall_async():
    store = InMemoryStore()
    n = _node(tags=["async-test"])
    store.write(n)
    results = await recall_async("query", "u1", store, tags=["async-test"])
    assert n in results


@pytest.mark.asyncio
async def test_recall_async_with_noop_embedder():
    store = InMemoryStore()
    n = _node(content="embedder test")
    store.write(n)
    embedder = NoopEmbeddingProvider(dimensions=4)
    results = await recall_async("embedder test", "u1", store, embedder=embedder)
    # NoopEmbeddingProvider returns zero vectors — should still return nodes
    assert isinstance(results, list)
