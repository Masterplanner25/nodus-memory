"""Phase H: EmbeddingProvider ABC, NoOpProvider, recall_similar stub."""
from __future__ import annotations

import math
import pytest


class TestEmbeddingProviderABC:
    def test_noop_provider_instantiable(self):
        from nodus_memory.embedding import NoOpProvider
        p = NoOpProvider()
        assert p.dimensions == 1536

    def test_noop_embed_returns_zeros(self):
        from nodus_memory.embedding import NoOpProvider
        p = NoOpProvider()
        vec = p.embed("hello world")
        assert len(vec) == 1536
        assert all(v == 0.0 for v in vec)

    def test_noop_custom_dimensions(self):
        from nodus_memory.embedding import NoOpProvider
        p = NoOpProvider(dimensions=256)
        vec = p.embed("test")
        assert len(vec) == 256
        assert p.dimensions == 256

    def test_custom_provider_can_be_implemented(self):
        from nodus_memory.embedding import EmbeddingProvider

        class FakeProvider(EmbeddingProvider):
            def embed(self, text: str) -> list[float]:
                return [float(len(text))] * 4

            @property
            def dimensions(self) -> int:
                return 4

        p = FakeProvider()
        vec = p.embed("hi")
        assert vec == [2.0, 2.0, 2.0, 2.0]
        assert p.dimensions == 4

    def test_abstract_cannot_be_instantiated(self):
        from nodus_memory.embedding import EmbeddingProvider
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore


class TestCosineSimilarity:
    def test_identical_vectors(self):
        from nodus_memory.embedding import cosine_similarity
        a = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(a, a) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        from nodus_memory.embedding import cosine_similarity
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-9

    def test_opposite_vectors(self):
        from nodus_memory.embedding import cosine_similarity
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-9

    def test_zero_vector_returns_zero(self):
        from nodus_memory.embedding import cosine_similarity
        z = [0.0, 0.0, 0.0]
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(z, a) == 0.0
        assert cosine_similarity(a, z) == 0.0

    def test_known_similarity(self):
        from nodus_memory.embedding import cosine_similarity
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        expected = 1.0 / math.sqrt(2)
        assert abs(cosine_similarity(a, b) - expected) < 1e-9


class TestRecallSimilar:
    def test_noop_provider_returns_empty(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        from nodus_memory.embedding import NoOpProvider
        store = MemoryStore(MemoryConfig(tenant_id="alice"), embedding_provider=NoOpProvider())
        store.put("k", "some text")
        results = store.recall_similar("some text")
        assert results == []

    def test_real_provider_returns_matches(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        from nodus_memory.embedding import EmbeddingProvider
        import dataclasses

        class ConstProvider(EmbeddingProvider):
            """All texts embed to the same vector — 100% similarity."""
            def embed(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0, 0.0]

            @property
            def dimensions(self) -> int:
                return 4

        store = MemoryStore(MemoryConfig(tenant_id="alice"), embedding_provider=ConstProvider())
        node = store.put("k", "text")
        # Manually set embedding (production would call embed pipeline)
        from nodus_memory.address import build_path
        store._backend.update(node.path, embedding=[1.0, 0.0, 0.0, 0.0])
        results = store.recall_similar("any text", threshold=0.9)
        assert any(n.key == "k" for n in results)

    def test_below_threshold_excluded(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        from nodus_memory.embedding import EmbeddingProvider
        import dataclasses

        class SparseProvider(EmbeddingProvider):
            def embed(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0, 0.0]

            @property
            def dimensions(self) -> int:
                return 4

        store = MemoryStore(MemoryConfig(tenant_id="alice"), embedding_provider=SparseProvider())
        node = store.put("k", "text")
        # Set embedding that is orthogonal to query — similarity = 0
        store._backend.update(node.path, embedding=[0.0, 1.0, 0.0, 0.0])
        results = store.recall_similar("any text", threshold=0.9)
        assert results == []

    def test_top_k_limits_results(self):
        from nodus_memory.config import MemoryConfig
        from nodus_memory.store import MemoryStore
        from nodus_memory.embedding import EmbeddingProvider

        class ConstProvider(EmbeddingProvider):
            def embed(self, text: str) -> list[float]:
                return [1.0, 0.0]

            @property
            def dimensions(self) -> int:
                return 2

        store = MemoryStore(MemoryConfig(tenant_id="alice"), embedding_provider=ConstProvider())
        for i in range(10):
            node = store.put(f"k{i}", f"text{i}")
            store._backend.update(node.path, embedding=[1.0, 0.0])
        results = store.recall_similar("q", top_k=3, threshold=0.5)
        assert len(results) <= 3
