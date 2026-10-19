from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import mde


def test_package_can_be_imported() -> None:
    assert mde.__package_name__ == "mde-core"


def test_package_has_description() -> None:
    assert "Core automation engine" in mde.__description__


def test_version_uses_semantic_version_format() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", mde.__version__) is not None


def test_build_and_lock_versions_match_runtime() -> None:
    root = Path(__file__).resolve().parents[3]
    for relative in ("pyproject.toml", "packages/mde-core/pyproject.toml"):
        config = tomllib.loads((root / relative).read_text(encoding="utf-8"))
        assert config["project"]["version"] == mde.__version__, relative

    for relative in ("uv.lock", "apps/autoknowledge-lite/uv.lock"):
        lock = tomllib.loads((root / relative).read_text(encoding="utf-8"))
        versions = [p["version"] for p in lock["package"] if p["name"] == "mde-core"]
        assert versions == [mde.__version__], relative


def test_installed_version_matches_runtime_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import importlib.metadata as metadata, json, mde; "
            "print(json.dumps([metadata.version('mde-core'), mde.__version__]))",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == [mde.__version__, mde.__version__]


def test_save_quality_tools_are_declared_and_locked() -> None:
    root = Path(__file__).resolve().parents[3]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        re.split(r"[<>=!~;\[]", requirement)[0]
        for requirement in config["dependency-groups"]["dev"]
    }
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = {package["name"] for package in lock["package"]}
    assert {"black", "ruff", "pytest"} <= declared & locked
