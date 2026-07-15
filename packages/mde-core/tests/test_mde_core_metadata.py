from __future__ import annotations
import re
import mde

def test_package_can_be_imported() -> None:
    assert mde.__package_name__ == "mde-core"

def test_package_has_description() -> None:
    assert "Core automation engine" in mde.__description__

def test_version_uses_semantic_version_format() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", mde.__version__) is not None
