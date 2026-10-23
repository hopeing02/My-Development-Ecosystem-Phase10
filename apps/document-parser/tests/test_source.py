"""Verify the source contract using metadata only, without document fixtures."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from os import stat_result
from pathlib import Path
from stat import S_IFDIR, S_IFIFO, S_IFREG
from unittest.mock import Mock, patch

import pytest

from document_parser import DocumentSource, validate_source


@pytest.fixture
def regular_file() -> Iterator[Mock]:
    """Model an existing regular file without creating or opening one."""
    metadata = stat_result((S_IFREG | 0o444, 0, 0, 1, 0, 0, 123, 0, 0, 0))
    with patch.object(Path, "stat", return_value=metadata) as stat:
        yield stat


@pytest.mark.parametrize(
    ("suffix", "expected_format"),
    [(".hwp", "hwp"), (".hwpx", "hwpx"), (".pdf", "pdf"), (".PdF", "pdf")],
)
@pytest.mark.parametrize("as_string", [False, True])
def test_supported_source(
    regular_file: Mock, suffix: str, expected_format: str, as_string: bool
) -> None:
    """Accept string and Path inputs while preserving a relative Unicode path."""
    path = Path("일반 문서") / f"report{suffix}"
    result = validate_source(str(path) if as_string else path)
    assert result == DocumentSource(path=path, format=expected_format)
    regular_file.assert_called_once_with()


@pytest.mark.parametrize("name", ["file.txt", "file", "file.pdf.exe", ".pdf"])
def test_unsupported_suffix(regular_file: Mock, name: str) -> None:
    """Reject unsupported or missing final suffixes on existing files."""
    with pytest.raises(ValueError, match="Supported source extensions"):
        validate_source(name)
    regular_file.assert_called_once_with()


@pytest.mark.parametrize("name", ["missing.pdf", "missing.txt"])
def test_missing_file(regular_file: Mock, name: str) -> None:
    """Report a missing file before checking its suffix."""
    error = FileNotFoundError(name)
    regular_file.side_effect = error
    with pytest.raises(FileNotFoundError) as caught:
        validate_source(name)
    assert caught.value is error


@pytest.mark.parametrize("mode", [S_IFDIR, S_IFIFO])
def test_non_regular_source(regular_file: Mock, mode: int) -> None:
    """Reject directories and special files even with a supported suffix."""
    regular_file.return_value = stat_result((mode, 0, 0, 1, 0, 0, 0, 0, 0, 0))
    with pytest.raises(ValueError, match="regular file"):
        validate_source("directory.pdf")


@pytest.mark.parametrize("error", [PermissionError("denied"), OSError("failure")])
def test_filesystem_error(regular_file: Mock, error: OSError) -> None:
    """Preserve filesystem failures instead of reporting successful validation."""
    regular_file.side_effect = error
    with pytest.raises(type(error)) as caught:
        validate_source("file.pdf")
    assert caught.value is error


def test_empty_path(regular_file: Mock) -> None:
    """Reject an empty string without treating it as the current directory."""
    with pytest.raises(ValueError, match="must not be empty"):
        validate_source("")
    regular_file.assert_not_called()


@pytest.mark.parametrize("path", [None, 42, b"file.pdf"])
def test_invalid_path_type(regular_file: Mock, path: object) -> None:
    """Reject values outside the string-based path contract before stat."""
    with pytest.raises(TypeError):
        validate_source(path)
    regular_file.assert_not_called()


def test_result_is_immutable(regular_file: Mock) -> None:
    """Keep the validated result immutable."""
    result = validate_source("file.pdf")
    with pytest.raises(FrozenInstanceError):
        result.format = "hwp"


def test_content_is_never_opened(regular_file: Mock) -> None:
    """Fail if validation attempts a content read or write through file opens."""
    with (
        patch("builtins.open", side_effect=AssertionError("content access")),
        patch("io.open", side_effect=AssertionError("content access")),
        patch("os.open", side_effect=AssertionError("content access")),
    ):
        assert validate_source("file.pdf").format == "pdf"
    regular_file.assert_called_once_with()
