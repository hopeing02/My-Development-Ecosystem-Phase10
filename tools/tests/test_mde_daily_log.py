"""Regression tests of D1 and D2 behavior; production verification is separate."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import mde_daily_log, mde_daily_plan

TOOLS = Path(__file__).resolve().parents[1]


class DailyLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (
            "autoknowledge-lite",
            "document-parser",
            "knowledge-viewer",
            "yeominjeon-auto-recharge",
            "sample-project",
        ):
            (self.root / "apps" / name).mkdir(parents=True)
        (self.root / "packages" / "mde-core").mkdir(parents=True)
        self.log = (
            self.root / "docs" / "14_operations" / "DevelopmentLog" / "2026-10-31.md"
        )

    def run_cli(self, tool: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(TOOLS / tool),
                "--root",
                str(self.root),
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=20,
            check=False,
        )

    def record(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "mde_daily_log.py",
            "record",
            "--date",
            "2026-10-31",
            "--project",
            "document-parser",
            "--step",
            "DOC-PARSER-1",
            "--work",
            "실제 업무 문서 검증",
            "--result",
            "입력과 결과 확인",
            "--minutes",
            "40",
            *args,
        )

    def test_record_on_existing_d1_plan_and_show(self) -> None:
        planned = self.run_cli(
            "mde_daily_plan.py",
            "plan",
            "--date",
            "2026-10-31",
            "--project",
            "document-parser",
            "--step",
            "DOC-PARSER-1",
            "--goal",
            "문서 확인",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        before = self.log.read_text(encoding="utf-8")
        result = self.record(
            "--verification",
            "검증완료",
            "--evidence",
            "실제 조회 확인",
            "--problem",
            "조회 결과 문제",
            "--solution",
            "입력 수정",
            "--next",
            "다음 점검",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        after = self.log.read_text(encoding="utf-8")
        self.assertIn("[D1 계획]", after)
        self.assertIn("실제 업무 문서 검증", after)
        self.assertIn("[D2 문제]", after)
        self.assertIn("[D2 해결]", after)
        self.assertIn("[D2 다음]", after)
        self.assertIn("실제: 40분", after)
        self.assertIn("실제 조회 확인", after)
        self.assertIn("- 미기록", after)
        self.assertIn("## 소요시간", after)
        self.assertEqual(after.count("## 오늘 작업"), 1)
        self.assertEqual(after.count("## 문제점"), 1)
        self.assertEqual(after.count("## 해결"), 1)
        self.assertEqual(after.count("## 내일 작업"), 1)
        self.assertEqual(after.count("## 소요시간"), 1)
        self.assertTrue(all(line in after for line in before.splitlines()))
        shown = self.run_cli("mde_daily_log.py", "show", "--date", "2026-10-31")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("[D2 실적]", shown.stdout)

    def test_allow_mde_core_without_d1_plan(self) -> None:
        result = self.record("--project", "mde-core", "--step", "MDE-D2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("프로젝트: `mde-core`", self.log.read_text(encoding="utf-8"))

    def test_disallow_duplicate_same_project_step(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        before = self.log.read_text(encoding="utf-8")
        second = self.record()
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(before, self.log.read_text(encoding="utf-8"))

    def test_allow_second_different_step(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        result = self.record("--step", "DOC-PARSER-2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D2 실적]"), 2)

    def test_reject_unknown_project(self) -> None:
        result = self.record("--project", "studyhub")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_reject_sample_project(self) -> None:
        result = self.record("--project", "sample-project")
        self.assertNotEqual(result.returncode, 0)

    def test_require_verification_evidence(self) -> None:
        result = self.record("--verification", "검증완료")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_no_fake_verified_status_by_default(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        self.assertIn("검증: 미검증", self.log.read_text(encoding="utf-8"))

    def test_reject_multiline_and_separator(self) -> None:
        self.assertNotEqual(self.record("--work", "위험\n## 조작").returncode, 0)
        self.assertNotEqual(self.record("--result", "결과 | 조작").returncode, 0)
        self.assertFalse(self.log.exists())

    def test_preserve_existing_five_sections(self) -> None:
        self.log.parent.mkdir(parents=True, exist_ok=True)
        original = (
            "# 원래 기록\n\n## 오늘 작업\n기존 작업 내용\n\n"
            "## 문제점\n기존 문제\n\n## 해결\n기존 해결\n\n"
            "## 내일 작업\n기존 내일\n\n## 소요시간\n기존 시간\n"
        )
        self.log.write_text(original, encoding="utf-8")
        self.assertEqual(self.record().returncode, 0)
        updated = self.log.read_text(encoding="utf-8")
        self.assertTrue(all(line in updated for line in original.splitlines()))
        self.assertEqual(updated.count("##"), 5)

    def test_reject_broken_existing_log(self) -> None:
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text("# 일지\n\n## 오늘 작업\n기존\n", encoding="utf-8")
        self.assertNotEqual(self.record().returncode, 0)
        self.assertEqual(
            self.log.read_text(encoding="utf-8"), "# 일지\n\n## 오늘 작업\n기존\n"
        )

    def test_unmeasured_time_is_not_invented(self) -> None:
        result = self.run_cli(
            "mde_daily_log.py",
            "record",
            "--date",
            "2026-10-31",
            "--project",
            "mde-core",
            "--step",
            "MDE-D2",
            "--work",
            "실제 일지 기록 확인",
            "--result",
            "저장 결과 확인",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("실제: 미계측", self.log.read_text(encoding="utf-8"))

    def test_reject_out_of_range_minutes(self) -> None:
        self.assertNotEqual(self.record("--minutes", "900").returncode, 0)

    def test_reject_invalid_day(self) -> None:
        result = self.record("--date", "2026-02-30")
        self.assertNotEqual(result.returncode, 0)

    def test_preserve_bom_crlf_and_blank_lines_byte_for_byte(self) -> None:
        self.log.parent.mkdir(parents=True)
        template = (
            "\ufeff# 기록\n\n"
            + "\n\n".join(
                f"## {heading} \t\n기존 {heading}" for heading in mde_daily_log.HEADINGS
            )
            + "\n"
        )
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                original = template.replace("\n", newline).encode("utf-8")
                self.log.write_bytes(original)
                result = self.record(
                    "--problem",
                    "문제 확인",
                    "--solution",
                    "원인 해결",
                    "--next",
                    "다음 확인",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                updated = self.log.read_bytes()
                retained = b"".join(
                    line
                    for line in updated.splitlines(keepends=True)
                    if not line.startswith(b"- [D2 ")
                )
                self.assertEqual(retained, original)

    def test_amend_preserves_original_and_rejects_duplicate_amendment(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        original = self.log.read_bytes()
        command = (
            "amend",
            "--date",
            "2026-10-31",
            "--project",
            "document-parser",
            "--step",
            "DOC-PARSER-1",
            "--work",
            "보완한 실제 업무 문서 검증",
            "--result",
            "재조회 결과 보완",
            "--problem",
            "기존 문제 보충",
            "--solution",
            "수정 근거 추가",
            "--next",
            "다음 확인",
        )
        result = self.run_cli("mde_daily_log.py", *command)
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = self.log.read_bytes()
        retained = b"".join(
            line
            for line in updated.splitlines(keepends=True)
            if not line.startswith("- [D2 보완".encode("utf-8"))
        )
        self.assertEqual(retained, original)
        self.assertEqual(updated.decode("utf-8").count("[D2 실적]"), 1)
        duplicate = self.run_cli("mde_daily_log.py", *command)
        self.assertEqual(duplicate.returncode, 1)
        self.assertEqual(self.log.read_bytes(), updated)

    def test_amend_requires_original_record(self) -> None:
        result = self.run_cli(
            "mde_daily_log.py",
            "amend",
            "--project",
            "mde-core",
            "--step",
            "MDE-D2",
            "--date",
            "2026-10-31",
            "--work",
            "보완",
            "--result",
            "확인",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.log.exists())

    def test_amend_evidence_required_for_verified_status(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        before = self.log.read_bytes()
        result = self.run_cli(
            "mde_daily_log.py",
            "amend",
            "--project",
            "document-parser",
            "--step",
            "DOC-PARSER-1",
            "--date",
            "2026-10-31",
            "--work",
            "검증 보완",
            "--result",
            "결과 확인",
            "--verification",
            "검증완료",
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.log.read_bytes(), before)

    def test_core_project_requires_real_in_repository_directory(self) -> None:
        (self.root / "packages" / "mde-core").rmdir()
        result = self.record("--project", "mde-core")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.log.exists())

    def test_different_projects_same_step_can_be_recorded(self) -> None:
        self.assertEqual(self.record().returncode, 0)
        result = self.record("--project", "knowledge-viewer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D2 실적]"), 2)

    def test_heading_at_eof_gets_a_new_time_line(self) -> None:
        self.log.parent.mkdir(parents=True)
        self.log.write_text(
            "# 기록\n\n"
            + "\n\n".join(f"## {heading}" for heading in mde_daily_log.HEADINGS),
            encoding="utf-8",
        )
        result = self.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## 소요시간\n- [D2 시간]", self.log.read_text(encoding="utf-8"))

    def test_unknown_duplicate_or_reordered_heading_refuses_write(self) -> None:
        self.log.parent.mkdir(parents=True)
        for headings in (
            (*mde_daily_log.HEADINGS, "추가 제목"),
            (*mde_daily_log.HEADINGS, "오늘 작업"),
            tuple(reversed(mde_daily_log.HEADINGS)),
        ):
            with self.subTest(headings=headings):
                original = (
                    "# 기록\n\n" + "\n".join(f"## {name}" for name in headings)
                ).encode("utf-8")
                self.log.write_bytes(original)
                self.assertEqual(self.record().returncode, 1)
                self.assertEqual(self.log.read_bytes(), original)

    def test_direct_call_minutes_types_and_boundaries(self) -> None:
        for minutes in (True, 1.5, "40", 0, 721):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                mde_daily_log.record_work(
                    self.root,
                    "2026-10-31",
                    "mde-core",
                    "MDE-D2",
                    "작업",
                    "결과",
                    minutes,
                    "미검증",
                )
        for day, minutes in (("2026-10-30", 1), ("2026-10-31", 720)):
            with self.subTest(minutes=minutes):
                path = mde_daily_log.record_work(
                    self.root,
                    day,
                    "mde-core",
                    "MDE-D2",
                    "작업",
                    "결과",
                    minutes,
                    "미검증",
                )
                self.assertIn(f"실제: {minutes}분", path.read_text(encoding="utf-8"))

    def test_invalid_text_status_and_evidence_are_rejected(self) -> None:
        for flag, value in (
            ("--work", ""),
            ("--work", " 공백"),
            ("--result", "결과 "),
            ("--work", "x" * 251),
            ("--work", "제어\x01문자"),
            ("--result", "줄\u2028바꿈"),
            ("--step", "../escape"),
            ("--verification", "PASS"),
            ("--verification", "검증실패"),
        ):
            with self.subTest(flag=flag, value=value):
                result = self.record(flag, value)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.log.exists())

    def test_show_missing_date_does_not_create_files(self) -> None:
        result = self.run_cli("mde_daily_log.py", "show", "--date", "2026-10-31")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("개발일지가 없습니다", result.stdout)
        self.assertFalse((self.root / "docs").exists())

    def test_existing_d1_lock_is_preserved(self) -> None:
        self.log.parent.mkdir(parents=True)
        lock = self.log.with_suffix(".md.d1-lock")
        lock.write_text("active", encoding="utf-8")
        result = self.record()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(lock.read_text(encoding="utf-8"), "active")
        self.assertFalse(self.log.exists())

    def test_failed_atomic_write_preserves_existing_content(self) -> None:
        mde_daily_plan.register_plan(
            self.root, "2026-10-31", "document-parser", "D1", "확인", 120
        )
        original = self.log.read_bytes()
        with patch.object(
            mde_daily_log.os, "replace", side_effect=OSError("disk failure")
        ):
            with self.assertRaises(OSError):
                mde_daily_log.record_work(
                    self.root,
                    "2026-10-31",
                    "mde-core",
                    "MDE-D2",
                    "작업",
                    "결과",
                    None,
                    "미검증",
                )
        self.assertEqual(self.log.read_bytes(), original)
        self.assertEqual(list(self.log.parent.iterdir()), [self.log])

    def test_concurrent_duplicate_record_is_written_once(self) -> None:
        command = [
            sys.executable,
            str(TOOLS / "mde_daily_log.py"),
            "--root",
            str(self.root),
            "record",
            "--date",
            "2026-10-31",
            "--project",
            "mde-core",
            "--step",
            "MDE-D2",
            "--work",
            "동시 기록",
            "--result",
            "동작 확인",
        ]
        processes = [
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
            for _ in range(4)
        ]
        for process in processes:
            process.communicate(timeout=20)
        self.assertEqual(sum(process.returncode == 0 for process in processes), 1)
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D2 실적]"), 1)
        self.assertFalse(self.log.with_suffix(".md.d1-lock").exists())

    def test_outside_log_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            link = self.root / "docs"
            try:
                link.symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("Windows symlink creation requires additional privileges")
            self.addCleanup(link.unlink)
            self.assertEqual(self.record().returncode, 1)
            self.assertEqual(list(Path(external).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
