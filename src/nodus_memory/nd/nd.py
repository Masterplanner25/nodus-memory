from __future__ import annotations

import pathlib


def get_nd_root() -> str:
    """Return the absolute path to the nodus_memory nd/ directory.

    This is the nodus.nd entry-point. The Nodus runtime calls this to resolve
    `import "nodus-memory"` to the directory containing index.nd.
    """
    return str(pathlib.Path(__file__).parent.resolve())
