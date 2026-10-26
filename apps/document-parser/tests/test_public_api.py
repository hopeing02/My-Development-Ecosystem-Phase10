"""The original STEP API reuses verified validation and preserves old callers."""

import os
from pathlib import Path
from unittest.mock import patch

from document_parser import (
    DocumentSource,
    inspect_document_source,
    source,
    validate_source,
)


def test_original_and_existing_keyword_calls(tmp_path: Path) -> None:
    path = tmp_path / "sample.HWPX"
    path.touch()
    expected = DocumentSource(path=path, format="hwpx")
    assert inspect_document_source(file_path=path) == expected
    assert validate_source(path=path) == expected


def test_new_api_reuses_existing_validation(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    path.touch()
    with patch.object(source, "validate_source", wraps=validate_source) as reused:
        assert inspect_document_source(path).format == "pdf"
    reused.assert_called_once_with(path)


def test_original_home_expansion(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))
    path = tmp_path / "sample.pdf"
    path.touch()
    assert inspect_document_source("~/sample.pdf").path == path
