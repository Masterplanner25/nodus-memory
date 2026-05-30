from __future__ import annotations

from nodus_memory.config import MemoryConfig
from nodus_memory.embedding import EmbeddingProvider, NoOpProvider
from nodus_memory.errors import (
    BackendError,
    CausalCycleError,
    EmbeddingError,
    InvalidAddressError,
    KeyNotFoundError,
    MemoryError,
    TenantError,
)
from nodus_memory.model import MemoryNode
from nodus_memory.nodus_bindings import attach_to_runtime
from nodus_memory.store import MemoryStore

__version__ = "0.1.0"

__all__ = [
    # Config
    "MemoryConfig",
    # Core
    "MemoryStore",
    "MemoryNode",
    # Embedding
    "EmbeddingProvider",
    "NoOpProvider",
    # Bindings
    "attach_to_runtime",
    # Errors
    "MemoryError",
    "KeyNotFoundError",
    "TenantError",
    "BackendError",
    "EmbeddingError",
    "CausalCycleError",
    "InvalidAddressError",
    # Version
    "__version__",
]
