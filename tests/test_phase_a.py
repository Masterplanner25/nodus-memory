"""Phase A: package skeleton — imports, version, config, error hierarchy."""
from __future__ import annotations

import importlib
import pytest


class TestPackageImports:
    def test_top_level_import(self):
        import nodus_memory  # noqa: F401

    def test_version_string(self):
        import nodus_memory
        assert nodus_memory.__version__ == "0.1.0"

    def test_all_exports_importable(self):
        from nodus_memory import (
            MemoryConfig,
            MemoryError,
            KeyNotFoundError,
            TenantError,
            BackendError,
            EmbeddingError,
            CausalCycleError,
            InvalidAddressError,
        )
        assert all(x is not None for x in [
            MemoryConfig, MemoryError, KeyNotFoundError, TenantError,
            BackendError, EmbeddingError, CausalCycleError, InvalidAddressError,
        ])

    def test_no_database_import_at_top_level(self):
        """Package must import cleanly without sqlalchemy installed."""
        import nodus_memory
        # If we got here without ImportError, sqlalchemy is not a hard dep
        assert nodus_memory.__version__

    def test_nd_entry_point(self):
        import pathlib
        from nodus_memory.nd.nd import get_nd_root
        root = get_nd_root()
        assert pathlib.Path(root).is_dir()
        assert (pathlib.Path(root) / "index.nd").exists()


class TestMemoryConfig:
    def test_default_config(self):
        from nodus_memory import MemoryConfig
        cfg = MemoryConfig()
        assert cfg.backend == "memory"
        assert cfg.tenant_id == "default"
        assert cfg.namespace == "default"
        assert cfg.embedding_provider == "noop"
        assert cfg.max_recall_limit == 100

    def test_custom_config(self):
        from nodus_memory import MemoryConfig
        cfg = MemoryConfig(tenant_id="alice", namespace="agent", max_recall_limit=50)
        assert cfg.tenant_id == "alice"
        assert cfg.namespace == "agent"
        assert cfg.max_recall_limit == 50

    def test_sqlalchemy_backend_requires_db_url(self):
        from nodus_memory import MemoryConfig
        with pytest.raises(ValueError, match="db_url"):
            MemoryConfig(backend="sqlalchemy")

    def test_sqlalchemy_backend_with_db_url(self):
        from nodus_memory import MemoryConfig
        cfg = MemoryConfig(backend="sqlalchemy", db_url="sqlite:///:memory:")
        assert cfg.backend == "sqlalchemy"

    def test_invalid_backend_rejected(self):
        from nodus_memory import MemoryConfig
        with pytest.raises(ValueError, match="unsupported backend"):
            MemoryConfig(backend="redis")

    def test_empty_tenant_id_rejected(self):
        from nodus_memory import MemoryConfig
        with pytest.raises(ValueError, match="tenant_id"):
            MemoryConfig(tenant_id="")

    def test_empty_namespace_rejected(self):
        from nodus_memory import MemoryConfig
        with pytest.raises(ValueError, match="namespace"):
            MemoryConfig(namespace="")


class TestErrorHierarchy:
    def test_all_errors_are_memory_error_subclasses(self):
        from nodus_memory import (
            MemoryError,
            KeyNotFoundError,
            TenantError,
            BackendError,
            EmbeddingError,
            CausalCycleError,
            InvalidAddressError,
        )
        for cls in [KeyNotFoundError, TenantError, BackendError,
                    EmbeddingError, CausalCycleError, InvalidAddressError]:
            assert issubclass(cls, MemoryError), f"{cls} not a MemoryError subclass"

    def test_all_errors_are_exception_subclasses(self):
        from nodus_memory import MemoryError
        assert issubclass(MemoryError, Exception)

    def test_key_not_found_includes_key(self):
        from nodus_memory import KeyNotFoundError
        err = KeyNotFoundError("my-key")
        assert err.key == "my-key"
        assert "my-key" in str(err)

    def test_tenant_error_default_message(self):
        from nodus_memory import TenantError
        err = TenantError()
        assert "tenant" in str(err)

    def test_causal_cycle_includes_key(self):
        from nodus_memory import CausalCycleError
        err = CausalCycleError("loop-key")
        assert err.key == "loop-key"
        assert "loop-key" in str(err)

    def test_invalid_address_includes_path(self):
        from nodus_memory import InvalidAddressError
        err = InvalidAddressError("/bad/path")
        assert err.path == "/bad/path"
        assert "/bad/path" in str(err)

    def test_errors_catchable_as_base(self):
        from nodus_memory import MemoryError, KeyNotFoundError
        with pytest.raises(MemoryError):
            raise KeyNotFoundError("k")

    def test_seven_error_types_total(self):
        import nodus_memory
        error_types = [
            nodus_memory.MemoryError,
            nodus_memory.KeyNotFoundError,
            nodus_memory.TenantError,
            nodus_memory.BackendError,
            nodus_memory.EmbeddingError,
            nodus_memory.CausalCycleError,
            nodus_memory.InvalidAddressError,
        ]
        assert len(error_types) == 7
