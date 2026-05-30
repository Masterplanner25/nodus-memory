from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nodus_memory.store import MemoryStore

# Host function name prefix — avoids collisions with nodus-lang builtins.
_PREFIX = "nm_"

_FUNCTIONS = [
    ("recall_from", 1),   # nm_recall_from(key) -> value | nil
    ("share",       2),   # nm_share(key, value) -> nil
    ("forget",      1),   # nm_forget(key) -> bool
    ("recall_all",  1),   # nm_recall_all(tag) -> list of values
    ("tag",         2),   # nm_tag(key, tags_list) -> nil
    ("link",        2),   # nm_link(child_key, parent_key) -> nil
]


def attach_to_runtime(runtime: Any, store: "MemoryStore") -> None:
    """Register nodus-memory host functions on *runtime*, bound to *store*.

    After calling this, Nodus scripts that import "nodus-memory" can call
    recall_from(), share(), forget(), recall_all(), tag(), and link().

    Parameters
    ----------
    runtime:
        A ``NodusRuntime`` instance (from ``nodus.NodusRuntime``).
    store:
        The ``MemoryStore`` that backs the language-level operations.
    """
    runtime.register_function(
        _PREFIX + "recall_from",
        lambda key: store.get(key),
        arity=1,
    )
    runtime.register_function(
        _PREFIX + "share",
        # At the language level, share() persists to the default namespace so
        # recall_from() can retrieve it. Python callers use store.share() directly
        # for cross-namespace sharing.
        lambda key, value: store.put(key, value) and None,
        arity=2,
    )
    runtime.register_function(
        _PREFIX + "forget",
        lambda key: store.delete(key),
        arity=1,
    )
    runtime.register_function(
        _PREFIX + "recall_all",
        lambda tag: [n.value for n in store.recall_all(tag=tag if tag else None)],
        arity=1,
    )
    runtime.register_function(
        _PREFIX + "tag",
        lambda key, tags_list: store.tag(key, frozenset(tags_list or [])) and None,
        arity=2,
    )
    runtime.register_function(
        _PREFIX + "link",
        lambda child, parent: store.link(child, parent) and None,
        arity=2,
    )
