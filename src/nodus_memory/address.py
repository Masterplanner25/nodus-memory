from __future__ import annotations

from nodus_memory.errors import InvalidAddressError

_PREFIX = "/memory"
_PARTS = 4  # tenant / namespace / type / key


def build_path(tenant: str, namespace: str, type: str, key: str) -> str:
    _require_segment(tenant, "tenant")
    _require_segment(namespace, "namespace")
    _require_segment(type, "type")
    _require_segment(key, "key")
    return f"{_PREFIX}/{tenant}/{namespace}/{type}/{key}"


def parse_path(path: str) -> dict[str, str]:
    validate_path(path)
    parts = path[len(_PREFIX) + 1:].split("/")
    return {
        "tenant": parts[0],
        "namespace": parts[1],
        "type": parts[2],
        "key": parts[3],
    }


def validate_path(path: str) -> None:
    if not path.startswith(_PREFIX + "/"):
        raise InvalidAddressError(path)
    tail = path[len(_PREFIX) + 1:]
    parts = tail.split("/")
    if len(parts) != _PARTS or any(not p for p in parts):
        raise InvalidAddressError(path)


def path_prefix(tenant: str, namespace: str) -> str:
    _require_segment(tenant, "tenant")
    _require_segment(namespace, "namespace")
    return f"{_PREFIX}/{tenant}/{namespace}"


def path_prefix_type(tenant: str, namespace: str, type: str) -> str:
    _require_segment(tenant, "tenant")
    _require_segment(namespace, "namespace")
    _require_segment(type, "type")
    return f"{_PREFIX}/{tenant}/{namespace}/{type}"


def _require_segment(value: str, name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"MAS segment '{name}' must be a non-empty string")
