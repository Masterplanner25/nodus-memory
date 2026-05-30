"""Phase B: MemoryNode dataclass and MAS addressing."""
from __future__ import annotations

import dataclasses
import time
import pytest


class TestMemoryNode:
    def _make(self, **kw):
        from nodus_memory.model import MemoryNode
        from nodus_memory.address import build_path
        defaults = dict(
            tenant_id="alice",
            namespace="agent",
            key="my-key",
            value="hello",
            path=build_path("alice", "agent", "general", "my-key"),
        )
        defaults.update(kw)
        return MemoryNode.create(**defaults)

    def test_create_returns_memory_node(self):
        from nodus_memory.model import MemoryNode
        node = self._make()
        assert isinstance(node, MemoryNode)

    def test_create_assigns_uuid_id(self):
        import re
        node = self._make()
        assert re.match(r"[0-9a-f-]{36}", node.id)

    def test_create_default_type(self):
        node = self._make()
        assert node.type == "general"

    def test_create_custom_type(self):
        node = self._make(type="fact")
        assert node.type == "fact"

    def test_create_default_tags_empty(self):
        node = self._make()
        assert node.tags == frozenset()

    def test_create_custom_tags(self):
        node = self._make(tags=frozenset({"important", "ai"}))
        assert "important" in node.tags
        assert "ai" in node.tags

    def test_create_timestamps_set(self):
        before = time.time()
        node = self._make()
        after = time.time()
        assert before <= node.created_at <= after
        assert node.created_at == node.updated_at

    def test_create_default_scores(self):
        node = self._make()
        assert node.impact_score == 1.0
        assert node.usage_count == 0
        assert node.success_count == 0
        assert node.failure_count == 0

    def test_node_is_frozen(self):
        node = self._make()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            node.key = "new-key"  # type: ignore

    def test_replace_produces_new_node(self):
        node = self._make()
        updated = dataclasses.replace(node, usage_count=5)
        assert updated.usage_count == 5
        assert node.usage_count == 0
        assert updated.id == node.id

    def test_causal_parent_id_default_none(self):
        node = self._make()
        assert node.causal_parent_id is None

    def test_causal_parent_id_custom(self):
        node = self._make(causal_parent_id="parent-uuid")
        assert node.causal_parent_id == "parent-uuid"

    def test_embedding_default_none(self):
        node = self._make()
        assert node.embedding is None

    def test_two_nodes_have_different_ids(self):
        n1 = self._make()
        n2 = self._make()
        assert n1.id != n2.id

    def test_value_preserved(self):
        node = self._make(value={"x": 1, "y": [1, 2, 3]})
        assert node.value == {"x": 1, "y": [1, 2, 3]}


class TestMASAddress:
    def test_build_path_basic(self):
        from nodus_memory.address import build_path
        p = build_path("alice", "agent", "fact", "deadline")
        assert p == "/memory/alice/agent/fact/deadline"

    def test_build_path_structure(self):
        from nodus_memory.address import build_path
        p = build_path("t", "n", "type", "k")
        parts = p.split("/")
        assert parts[0] == ""
        assert parts[1] == "memory"
        assert parts[2] == "t"
        assert parts[3] == "n"
        assert parts[4] == "type"
        assert parts[5] == "k"

    def test_parse_path_round_trips(self):
        from nodus_memory.address import build_path, parse_path
        p = build_path("alice", "session", "event", "login-abc")
        parsed = parse_path(p)
        assert parsed == {"tenant": "alice", "namespace": "session", "type": "event", "key": "login-abc"}

    def test_validate_path_valid(self):
        from nodus_memory.address import validate_path
        validate_path("/memory/alice/agent/fact/key")  # no exception

    def test_validate_path_missing_prefix(self):
        from nodus_memory.address import validate_path
        from nodus_memory.errors import InvalidAddressError
        with pytest.raises(InvalidAddressError):
            validate_path("/alice/agent/fact/key")

    def test_validate_path_too_few_segments(self):
        from nodus_memory.address import validate_path
        from nodus_memory.errors import InvalidAddressError
        with pytest.raises(InvalidAddressError):
            validate_path("/memory/alice/agent/fact")

    def test_validate_path_too_many_segments(self):
        from nodus_memory.address import validate_path
        from nodus_memory.errors import InvalidAddressError
        with pytest.raises(InvalidAddressError):
            validate_path("/memory/alice/agent/fact/key/extra")

    def test_validate_path_empty_segment(self):
        from nodus_memory.address import validate_path
        from nodus_memory.errors import InvalidAddressError
        with pytest.raises(InvalidAddressError):
            validate_path("/memory/alice//fact/key")

    def test_path_prefix_basic(self):
        from nodus_memory.address import path_prefix
        p = path_prefix("alice", "agent")
        assert p == "/memory/alice/agent"

    def test_path_prefix_type_basic(self):
        from nodus_memory.address import path_prefix_type
        p = path_prefix_type("alice", "agent", "fact")
        assert p == "/memory/alice/agent/fact"

    def test_build_path_empty_tenant_rejected(self):
        from nodus_memory.address import build_path
        with pytest.raises(ValueError):
            build_path("", "ns", "type", "key")

    def test_build_path_empty_key_rejected(self):
        from nodus_memory.address import build_path
        with pytest.raises(ValueError):
            build_path("tenant", "ns", "type", "")

    def test_path_prefix_empty_namespace_rejected(self):
        from nodus_memory.address import path_prefix
        with pytest.raises(ValueError):
            path_prefix("tenant", "")

    def test_mas_hierarchy_ordering(self):
        from nodus_memory.address import path_prefix, path_prefix_type, build_path
        tenant, ns, typ, key = "t", "n", "tp", "k"
        p = build_path(tenant, ns, typ, key)
        prefix_ns = path_prefix(tenant, ns)
        prefix_type = path_prefix_type(tenant, ns, typ)
        assert p.startswith(prefix_type)
        assert prefix_type.startswith(prefix_ns)
