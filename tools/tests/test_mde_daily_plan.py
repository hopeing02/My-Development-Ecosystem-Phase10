"""Behavior tests for the MDE daily plan CLI using an isolated repository."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import mde_daily_plan

SCRIPT = Path(__file__).resolve().parents[1] / "mde_daily_plan.py"


class DailyPlanTests(unittest.TestCase):
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

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )

    def test_lists_only_real_apps(self) -> None:
        result = self.run_cli("projects")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "autoknowledge-lite",
                "document-parser",
                "knowledge-viewer",
                "yeominjeon-auto-recharge",
            ],
        )

    def test_register_show_and_prevent_duplicate(self) -> None:
        command = (
            "plan",
            "--date",
            "2026-10-28",
            "--project",
            "document-parser",
            "--step",
            "DOC-PARSER-1",
            "--goal",
            "문서 파서 검증",
        )
        first = self.run_cli(*command)
        self.assertEqual(first.returncode, 0, first.stderr)
        shown = self.run_cli("show", "--date", "2026-10-28")
        self.assertIn("document-parser", shown.stdout)
        self.assertIn("예정: 120분", shown.stdout)
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        original = log.read_bytes()
        self.assertNotEqual(self.run_cli(*command).returncode, 0)
        self.assertEqual(log.read_bytes(), original)
        self.assertEqual(
            [
                line
                for line in original.decode("utf-8").splitlines()
                if line.startswith("## ")
            ],
            ["## 오늘 작업", "## 문제점", "## 해결", "## 내일 작업", "## 소요시간"],
        )
        self.assertIn("실제: 미계측", original.decode("utf-8"))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["apps", "docs"])

    def test_preserves_existing_log(self) -> None:
        log = self.root / "docs" / "14_operations" / "DevelopmentLog" / "2026-10-28.md"
        log.parent.mkdir(parents=True)
        log.write_text(
            "# 이전 로그\n\n## 오늘 작업\n기존 내용\n\n## 문제점\n기존 오류\n",
            encoding="utf-8",
        )
        result = self.run_cli(
            "plan",
            "--date",
            "2026-10-28",
            "--project",
            "knowledge-viewer",
            "--step",
            "KV-1",
            "--goal",
            "화면 검증",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        new = log.read_text(encoding="utf-8")
        self.assertIn("기존 내용", new)
        self.assertIn("기존 오류", new)
        self.assertIn("knowledge-viewer", new)

    def test_rejects_unregistered_project(self) -> None:
        result = self.run_cli(
            "plan",
            "--date",
            "2026-10-28",
            "--project",
            "studyhub",
            "--step",
            "SH-1",
            "--goal",
            "임의 등록",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "docs").exists())

    def test_lists_directories_without_metadata_and_ignores_files(self) -> None:
        (self.root / "apps" / "not-an-app.txt").write_text("file", encoding="utf-8")
        self.assertEqual(len(mde_daily_plan.list_app_projects(self.root)), 4)

    def test_missing_apps_directory_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ValueError):
                mde_daily_plan.list_app_projects(Path(empty))

    def test_preserves_existing_bytes_with_bom_and_blank_lines(self) -> None:
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                original = (
                    (
                        "\ufeff# 개발일지\n\n## 오늘 작업 \t\n\n기존 내용\n\n"
                        "## 문제점\n기존 오류\n\n## 해결\n기록\n\n"
                        "## 내일 작업\n예정\n\n## 소요시간\n20분"
                    )
                    .replace("\n", newline)
                    .encode("utf-8")
                )
                log.write_bytes(original)
                mde_daily_plan.register_plan(
                    self.root, "2026-10-28", "document-parser", "D1", "검증", 30
                )
                updated = log.read_bytes()
                added = next(
                    line
                    for line in updated.decode("utf-8").splitlines()
                    if line.startswith(mde_daily_plan.PLAN_PREFIX)
                )
                self.assertEqual(
                    updated.replace((newline + added).encode("utf-8"), b"", 1),
                    original,
                )

    def test_heading_at_end_of_file_gets_a_separate_plan_line(self) -> None:
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        log.write_bytes("# 일지\n\n## 오늘 작업".encode("utf-8"))
        mde_daily_plan.register_plan(
            self.root, "2026-10-28", "knowledge-viewer", "KV-1", "화면 검증", 120
        )
        self.assertIn("\n- [D1 계획]", log.read_text(encoding="utf-8"))
        self.assertIn(
            "knowledge-viewer", mde_daily_plan.show_plan(self.root, "2026-10-28")
        )

    def test_missing_today_heading_is_rejected_without_changes(self) -> None:
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        for heading in ("## 문제점", "### 오늘 작업", "## 오늘 작업 extra"):
            with self.subTest(heading=heading):
                original = (heading + "\n원본").encode("utf-8")
                log.write_bytes(original)
                with self.assertRaises(ValueError):
                    mde_daily_plan.register_plan(
                        self.root, "2026-10-28", "document-parser", "D1", "검증", 120
                    )
                self.assertEqual(log.read_bytes(), original)
                self.assertEqual(list(log.parent.iterdir()), [log])

    def test_invalid_dates_are_rejected_by_cli_and_functions(self) -> None:
        for day in (
            "2026-02-29",
            "2026-13-01",
            "2026-1-01",
            "../outside",
            "2026-10-28/../../outside",
            "２０２６-１０-２８",
        ):
            with self.subTest(day=day):
                result = self.run_cli("show", "--date", day)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                with self.assertRaises(ValueError):
                    mde_daily_plan.show_plan(self.root, day)
                with self.assertRaises(ValueError):
                    mde_daily_plan.register_plan(
                        self.root, day, "document-parser", "D1", "검증", 120
                    )
        self.assertFalse((self.root / "docs").exists())

    def test_invalid_plan_inputs_do_not_write_files(self) -> None:
        cases = [
            ("--project", "sample-project"),
            ("--project", "../document-parser"),
            ("--project", "StudyHub"),
            ("--step", ""),
            ("--step", "한글"),
            ("--step", "D1\n"),
            ("--step", "D" * 65),
            ("--goal", "   "),
            ("--goal", "가" * 201),
            ("--goal", "줄\n바꿈"),
            ("--goal", "줄\r바꿈"),
            ("--goal", "줄\u2028바꿈"),
            ("--goal", "목표\n"),
            ("--minutes", "14"),
            ("--minutes", "721"),
            ("--minutes", "abc"),
        ]
        for flag, value in cases:
            with self.subTest(flag=flag, value=value):
                args = [
                    "plan",
                    "--date",
                    "2026-10-28",
                    "--project",
                    "document-parser",
                    "--step",
                    "D1",
                    "--goal",
                    "검증",
                    "--minutes",
                    "120",
                ]
                args[args.index(flag) + 1] = value
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.root / "docs").exists())

    def test_direct_call_rejects_non_integer_minutes_and_control_characters(
        self,
    ) -> None:
        for minutes in (True, 120.5, "120"):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                mde_daily_plan.register_plan(
                    self.root, "2026-10-28", "document-parser", "D1", "검증", minutes
                )
        for goal in ("가\x00나", "가\x85나", "가\u2029나"):
            with self.subTest(goal=goal), self.assertRaises(ValueError):
                mde_daily_plan.register_plan(
                    self.root, "2026-10-28", "document-parser", "D1", goal, 120
                )
        self.assertFalse((self.root / "docs").exists())

    def test_valid_boundaries_and_future_date(self) -> None:
        for day, minutes in (("2028-02-29", 15), ("2030-01-01", 720)):
            with self.subTest(day=day):
                log = mde_daily_plan.register_plan(
                    self.root,
                    day,
                    " yeominjeon-auto-recharge ",
                    "D" * 64,
                    "가" * 200,
                    minutes,
                )
                self.assertEqual(log.name, f"{day}.md")
                self.assertIn(
                    f"예정: {minutes}분", mde_daily_plan.show_plan(self.root, day)
                )

    def test_show_missing_log_and_missing_plan_are_read_only(self) -> None:
        result = self.run_cli("show", "--date", "2026-10-28")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("등록된 개발일지가 없습니다", result.stdout)
        self.assertFalse((self.root / "docs").exists())
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        original = "## 오늘 작업\n완료 기록\n".encode("utf-8")
        log.write_bytes(original)
        result = self.run_cli("show", "--date", "2026-10-28")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("D1 개발계획이 없습니다", result.stdout)
        self.assertEqual(log.read_bytes(), original)

    def test_atomic_update_failure_preserves_existing_log_and_cleans_up(self) -> None:
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        original = "## 오늘 작업\n기존 내용\n".encode("utf-8")
        log.write_bytes(original)
        with patch.object(
            mde_daily_plan.os, "replace", side_effect=OSError("write failed")
        ):
            with self.assertRaises(OSError):
                mde_daily_plan.register_plan(
                    self.root, "2026-10-28", "document-parser", "D1", "검증", 120
                )
        self.assertEqual(log.read_bytes(), original)
        self.assertEqual(list(log.parent.iterdir()), [log])

    def test_existing_lock_is_preserved_and_registration_stops(self) -> None:
        log = mde_daily_plan.daily_log_path(self.root, "2026-10-28")
        log.parent.mkdir(parents=True)
        lock = log.with_suffix(".md.d1-lock")
        lock.write_text("active", encoding="utf-8")
        result = self.run_cli(
            "plan",
            "--date",
            "2026-10-28",
            "--project",
            "document-parser",
            "--step",
            "D1",
            "--goal",
            "검증",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(log.exists())
        self.assertEqual(lock.read_text(encoding="utf-8"), "active")

    def test_concurrent_registrations_allow_one_plan(self) -> None:
        for existing_log in (False, True):
            with self.subTest(existing_log=existing_log):
                day = "2026-10-29" if existing_log else "2026-10-28"
                log = mde_daily_plan.daily_log_path(self.root, day)
                if existing_log:
                    log.parent.mkdir(parents=True, exist_ok=True)
                    log.write_text("## 오늘 작업\n기존 내용\n", encoding="utf-8")
                command = [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(self.root),
                    "plan",
                    "--date",
                    day,
                    "--project",
                    "document-parser",
                    "--step",
                    "D1",
                    "--goal",
                    "동시 등록 검증",
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
                self.assertEqual(sum(p.returncode == 0 for p in processes), 1)
                self.assertEqual(
                    log.read_text(encoding="utf-8").count("- [D1 계획]"), 1
                )
                if existing_log:
                    self.assertIn("기존 내용", log.read_text(encoding="utf-8"))

    def test_path_redirect_outside_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            link = self.root / "docs"
            try:
                link.symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("Windows symlink creation requires additional privileges")
            self.addCleanup(link.unlink)
            with self.assertRaises(ValueError):
                mde_daily_plan.register_plan(
                    self.root, "2026-10-28", "document-parser", "D1", "검증", 120
                )
            self.assertEqual(list(Path(external).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
