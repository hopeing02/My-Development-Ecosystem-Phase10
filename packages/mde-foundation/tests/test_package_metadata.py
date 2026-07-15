from __future__ import annotations

import re

import mde


def test_package_can_be_imported() -> None:
    assert mde.__package_name__ == "mde-foundation"


def test_package_has_description() -> None:
    assert mde.__description__ == "Shared foundation package for MDE applications"


def test_version_uses_semantic_version_format() -> None:
    version_pattern = r"^\d+\.\d+\.\d+$"

    assert re.match(version_pattern, mde.__version__) is not None
