"""Memory Address Space (MAS) — hierarchical path addressing for memory nodes.

Path structure:  /memory/{tenant_id}/{namespace}/{addr_type}/{node_id}

Query patterns:
    /memory/user-1/entities/updated/abc-123  → exact match
    /memory/user-1/entities/*                → all under entities
    /memory/user-1/entities/**              → recursive
"""
from __future__ import annotations

import fnmatch
import re
import uuid

MAS_ROOT = "/memory"
MAX_PATH_DEPTH = 6
LEGACY_NAMESPACE = "_legacy"

_DOUBLE_SLASH = re.compile(r"/+")
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_\-\.]+$")


def build_path(
    tenant_id: str,
    namespace: str,
    addr_type: str,
    node_id: Optional[str] = None,
) -> str:
    """Build a canonical MAS path.

    Args:
        tenant_id:  User/tenant identifier.
        namespace:  Logical signal group (e.g. ``"entities"``, ``"executions"``).
        addr_type:  Sub-category (e.g. ``"updated"``, ``"completed"``).
        node_id:    Optional leaf node ID. When None, returns the directory path.

    Returns:
        A path like ``/memory/user-1/entities/updated/abc-123``.
    """
    parts = [MAS_ROOT, tenant_id, namespace, addr_type]
    if node_id is not None:
        parts.append(node_id)
    path = "/".join(parts)
    return _DOUBLE_SLASH.sub("/", path)


def parse_path(path: str) -> dict:
    """Parse a MAS path into components.

    Returns:
        Dict with keys: ``root``, ``tenant_id``, ``namespace``, ``addr_type``,
        ``node_id`` (may be None).  Returns empty dict on malformed input.
    """
    if not path or not path.startswith(MAS_ROOT):
        return {}
    segments = [s for s in path.split("/") if s]
    if len(segments) < 1 or segments[0] != "memory":
        return {}
    result = {
        "root": MAS_ROOT,
        "tenant_id": segments[1] if len(segments) > 1 else None,
        "namespace": segments[2] if len(segments) > 2 else None,
        "addr_type": segments[3] if len(segments) > 3 else None,
        "node_id": segments[4] if len(segments) > 4 else None,
    }
    return result


def glob_match(path: str, pattern: str) -> bool:
    """Return True if *path* matches *pattern*.

    Supports:
    - ``*``  — matches one path segment
    - ``**`` — matches zero or more path segments (recursive)
    - Exact string comparison when no wildcards

    Examples::

        glob_match("/memory/u1/ent/upd/abc", "/memory/u1/ent/*")   → True
        glob_match("/memory/u1/ent/upd/abc", "/memory/u1/**")       → True
        glob_match("/memory/u1/ent/upd/abc", "/memory/u2/*")        → False
    """
    if "**" in pattern:
        # Convert ** to fnmatch multi-segment wildcard
        regex_pattern = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        return bool(re.fullmatch(regex_pattern, path))
    return fnmatch.fnmatch(path, pattern)


def derive_legacy_path(node_id: str, user_id: str, memory_type: str) -> str:
    """Derive a stable MAS path for a legacy node that lacks one."""
    return build_path(user_id, LEGACY_NAMESPACE, memory_type, node_id)


# Optional import for type hints
try:
    from typing import Optional
except ImportError:
    Optional = None  # type: ignore[assignment,misc]
