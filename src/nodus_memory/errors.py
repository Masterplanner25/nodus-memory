from __future__ import annotations


class MemoryError(Exception):
    """Base class for all nodus-memory errors."""


class KeyNotFoundError(MemoryError):
    def __init__(self, key: str) -> None:
        super().__init__(f"memory key not found: {key!r}")
        self.key = key


class TenantError(MemoryError):
    def __init__(self, msg: str = "tenant isolation violation") -> None:
        super().__init__(msg)


class BackendError(MemoryError):
    """Raised when the persistence backend encounters an unrecoverable error."""


class EmbeddingError(MemoryError):
    """Raised when the embedding provider fails."""


class CausalCycleError(MemoryError):
    def __init__(self, key: str) -> None:
        super().__init__(f"causal cycle detected at key: {key!r}")
        self.key = key


class InvalidAddressError(MemoryError):
    def __init__(self, path: str) -> None:
        super().__init__(f"invalid MAS address: {path!r}")
        self.path = path
