"""Expanded editions must preserve the STEP 01 outputs and every input file."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.ebook_ai.ebook_builder import EbookBuildError, build_ebook


@pytest.fixture
def book(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "한글 원고"
    root.mkdir()
    (root / "first.md").write_text("첫 장 원본\n", encoding="utf-8")
    (root / "second.md").write_text("두 번째 장 원본\n", encoding="utf-8")
    manifest = root / "book.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "가상 전자책",
                "chapters": [
                    {"title": "첫 장", "path": "first.md"},
                    {"title": "둘째 장", "path": "second.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    notes = root / "notes"
    notes.mkdir()
    (notes / "first.MD").write_bytes(
        "\ufeff표와 코드가 있는 승인 해설\r\n\r\n| 값 | 설명 |\r\n| --- | --- |\r\n| 1 | 가상 |\r\n\r\n```python\r\nprint('한글')\r\n```\r\n".encode(
            "utf-8"
        )
    )
    approved = root / "approved-supplements.json"
    approved.write_text(
        json.dumps(
            {
                "supplements": [
                    {"step": "chapter-001", "path": "notes/first.MD"},
                ]
            }
        ),
        encoding="utf-8-sig",
    )
    return manifest, approved


def test_expansion_preserves_inputs_base_outputs_and_order(book, tmp_path):
    manifest, approved = book
    output = tmp_path / "output"
    result = build_ebook(manifest, output)
    bases = (result.toc_path, result.basic_path)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino) for p in bases}
    sources = [p for p in manifest.parent.rglob("*") if p.is_file()]
    original = {p: p.read_bytes() for p in sources}
    assert build_ebook(manifest, output, supplements_path=approved) == result
    expanded = (output / "expanded.md").read_text(encoding="utf-8")
    supplement_body = (manifest.parent / "notes/first.MD").read_text(
        encoding="utf-8-sig"
    )
    assert expanded.index("첫 장 원본") < expanded.index("### 추가 해설")
    assert expanded.index("### 추가 해설") < expanded.index("두 번째 장 원본")
    assert expanded.count("### 추가 해설") == 1
    assert supplement_body in expanded
    assert (
        expanded.split('<a id="chapter-001"></a>')[0]
        == result.basic_path.read_text(encoding="utf-8").split(
            '<a id="chapter-001"></a>'
        )[0]
    )
    for anchor in ("chapter-001", "chapter-002"):
        assert f'<a id="{anchor}"></a>' in expanded
        assert f"](#{anchor})" in expanded
    assert before == {
        p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino) for p in bases
    }
    assert original == {p: p.read_bytes() for p in sources}


def test_step01_example_bytes_are_pinned_to_before_step02(tmp_path):
    manifest = Path(__file__).resolve().parents[1] / "examples/manifest.json"
    result = build_ebook(manifest, tmp_path / "plain")
    assert (
        hashlib.sha256(result.toc_path.read_bytes()).hexdigest()
        == "8b5bcc4c4d75d2f8a2d0be1b8328131e88f8eb237a9ad94fcd796d9f698e9002"
    )
    assert (
        hashlib.sha256(result.basic_path.read_bytes()).hexdigest()
        == "0d20f0884af089f4f0d4a31512eb2ac92aab08b6fb1bd2d791976eedaf1be3e2"
    )
    assert not (result.basic_path.parent / "expanded.md").exists()


def test_new_directory_repeatability_and_overwrite(book, tmp_path):
    manifest, approved = book
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_ebook(manifest, first, supplements_path=approved)
    build_ebook(manifest, second, supplements_path=approved)
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    assert before == {p.name: p.read_bytes() for p in second.iterdir()}
    with pytest.raises(EbookBuildError, match="exists"):
        build_ebook(manifest, first, supplements_path=approved)
    build_ebook(manifest, first, supplements_path=approved, overwrite=True)
    assert before == {p.name: p.read_bytes() for p in first.iterdir()}
    # Legacy calls neither generate nor remove an existing expanded edition.
    build_ebook(manifest, first, overwrite=True)
    assert before == {p.name: p.read_bytes() for p in first.iterdir()}


@pytest.mark.parametrize(
    "case",
    [
        "json",
        "encoding",
        "not_object",
        "empty",
        "not_list",
        "not_entry",
        "missing_step",
        "unknown",
        "duplicate",
        "duplicate_file",
        "missing_path",
        "empty_path",
        "bad_path_type",
        "null_path",
        "missing_file",
        "directory",
        "empty_file",
        "bad_file_encoding",
        "extension",
        "absolute",
        "windows_absolute",
        "windows_drive_relative",
        "unc",
        "parent",
        "backslash_parent",
        "ads",
        "original_as_supplement",
    ],
)
def test_invalid_supplement_preserves_all_outputs(book, tmp_path, case):
    manifest, approved = book
    output = tmp_path / "output"
    build_ebook(manifest, output)
    (output / "expanded.md").write_text("previous expanded", encoding="utf-8")
    before = {p: p.read_bytes() for p in output.iterdir()}
    entry = {"step": "chapter-001", "path": "notes/first.MD"}
    data = {"supplements": [entry]}
    note = manifest.parent / "notes/first.MD"
    if case == "not_object":
        data = []
    elif case == "empty":
        data["supplements"] = []
    elif case == "not_list":
        data["supplements"] = "file.md"
    elif case == "not_entry":
        data["supplements"] = ["file.md"]
    elif case == "missing_step":
        entry.pop("step")
    elif case == "unknown":
        entry["step"] = "STEP-01"
    elif case == "duplicate":
        data["supplements"].append(entry.copy())
    elif case == "duplicate_file":
        data["supplements"].append({**entry, "step": "chapter-002"})
    elif case == "missing_path":
        entry.pop("path")
    elif case == "empty_path":
        entry["path"] = ""
    elif case == "bad_path_type":
        entry["path"] = 1
    elif case == "null_path":
        entry["path"] = "\0.md"
    elif case == "missing_file":
        note.unlink()
    elif case == "directory":
        note.unlink()
        note.mkdir()
    elif case == "empty_file":
        note.write_text(" \n", encoding="utf-8")
    elif case == "bad_file_encoding":
        note.write_bytes(b"\xff")
    elif case == "extension":
        entry["path"] = "notes/first.txt"
    elif case == "absolute":
        entry["path"] = note.as_posix()
    elif case == "windows_absolute":
        entry["path"] = "C:\\outside.md"
    elif case == "windows_drive_relative":
        entry["path"] = "C:outside.md"
    elif case == "unc":
        entry["path"] = "\\\\server\\share\\outside.md"
    elif case == "parent":
        entry["path"] = "notes/../notes/first.MD"
    elif case == "backslash_parent":
        entry["path"] = "..\\outside.md"
    elif case == "ads":
        entry["path"] = "notes/first.MD:hidden.md"
    elif case == "original_as_supplement":
        entry["path"] = "first.md"
    if case == "json":
        approved.write_bytes(b"{")
    elif case == "encoding":
        approved.write_bytes(b"\xff")
    else:
        approved.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EbookBuildError):
        build_ebook(manifest, output, supplements_path=approved, overwrite=True)
    assert before == {p: p.read_bytes() for p in output.iterdir()}


def test_failed_validation_does_not_create_output(book, tmp_path):
    manifest, approved = book
    approved.unlink()
    output = tmp_path / "not_created"
    with pytest.raises(EbookBuildError, match="supplements JSON"):
        build_ebook(manifest, output, supplements_path=approved)
    assert not output.exists()


@pytest.mark.parametrize("overwrite", [False, True])
def test_changed_base_is_never_rewritten(book, tmp_path, overwrite):
    manifest, approved = book
    output = tmp_path / "output"
    result = build_ebook(manifest, output)
    result.basic_path.write_text("edited by user", encoding="utf-8")
    before = {p: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(EbookBuildError, match="differs; preserved"):
        build_ebook(manifest, output, supplements_path=approved, overwrite=overwrite)
    assert before == {p: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("alias", ["basic", "source", "supplement"])
def test_expanded_cannot_alias_protected_file(book, tmp_path, alias):
    manifest, approved = book
    output = tmp_path / "output"
    result = build_ebook(manifest, output)
    protected = {
        "basic": result.basic_path,
        "source": manifest.parent / "first.md",
        "supplement": manifest.parent / "notes/first.MD",
    }[alias]
    os.link(protected, output / "expanded.md")
    before = protected.read_bytes()
    with pytest.raises(EbookBuildError):
        build_ebook(manifest, output, supplements_path=approved, overwrite=True)
    assert protected.read_bytes() == before


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_supplement_cannot_escape_through_directory_link(book, tmp_path, kind):
    manifest, approved = book
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "extra.md").write_text("outside content", encoding="utf-8")
    link = manifest.parent / "link"
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("Windows junction test")
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                pytest.skip(
                    "Windows symlink privilege unavailable; junction tested separately"
                )
            raise
    approved.write_text(
        json.dumps({"supplements": [{"step": "chapter-001", "path": "link/extra.md"}]}),
        encoding="utf-8",
    )
    with pytest.raises(EbookBuildError, match="escapes input root"):
        build_ebook(manifest, tmp_path / "output", supplements_path=approved)
    assert not (tmp_path / "output").exists()


def test_atomic_replace_failure_preserves_old_expanded(book, tmp_path, monkeypatch):
    manifest, approved = book
    output = tmp_path / "output"
    build_ebook(manifest, output, supplements_path=approved)
    before = {p: p.read_bytes() for p in output.iterdir()}

    def fail_replace(*args):
        raise PermissionError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(PermissionError, match="simulated"):
        build_ebook(manifest, output, supplements_path=approved, overwrite=True)
    assert before == {p: p.read_bytes() for p in output.iterdir()}


def test_exclusive_publish_preserves_concurrent_output(book, tmp_path, monkeypatch):
    manifest, approved = book
    output = tmp_path / "output"
    build_ebook(manifest, output)

    def concurrent_link(source, target):
        Path(target).write_bytes(b"concurrent result")
        raise FileExistsError("simulated concurrent publisher")

    monkeypatch.setattr(os, "link", concurrent_link)
    with pytest.raises(FileExistsError, match="concurrent publisher"):
        build_ebook(manifest, output, supplements_path=approved)
    assert (output / "expanded.md").read_bytes() == b"concurrent result"
    assert not list(output.glob(".expanded-*.tmp"))


def test_expanded_cli(book, tmp_path):
    manifest, approved = book
    script = Path(__file__).resolve().parents[1] / "ebook_builder.py"
    command = [
        sys.executable,
        str(script),
        "--manifest",
        str(manifest),
        "--output-dir",
        str(tmp_path / "cli"),
        "--supplements",
        str(approved),
    ]
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cli/expanded.md").exists()
    approved.write_text("not json", encoding="utf-8")
    result = subprocess.run(command + ["--overwrite"], capture_output=True)
    assert result.returncode == 1
    assert b"Traceback" not in result.stderr
