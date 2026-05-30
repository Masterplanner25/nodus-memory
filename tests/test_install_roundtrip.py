"""Phase K — pip install -e . roundtrip: package installs cleanly and version matches."""
from __future__ import annotations

import importlib.metadata
import re


class TestInstallRoundtrip:
    def test_package_importable(self):
        import nodus_memory  # noqa: F401

    def test_version_matches_pyproject(self):
        import nodus_memory
        metadata_version = importlib.metadata.version("nodus-memory")
        assert nodus_memory.__version__ == metadata_version

    def test_version_is_semver(self):
        import nodus_memory
        assert re.match(r"^\d+\.\d+\.\d+$", nodus_memory.__version__)

    def test_nd_entry_point_registered(self):
        eps = importlib.metadata.entry_points(group="nodus.nd")
        names = [ep.name for ep in eps]
        assert "nodus-memory" in names, f"nodus-memory not in nodus.nd entry-points: {names}"

    def test_nd_root_exists(self):
        import pathlib
        from nodus_memory.nd.nd import get_nd_root
        root = pathlib.Path(get_nd_root())
        assert root.is_dir()
        assert (root / "index.nd").exists()

    def test_all_public_exports_importable(self):
        import nodus_memory
        for name in nodus_memory.__all__:
            assert hasattr(nodus_memory, name), f"Missing export: {name}"
