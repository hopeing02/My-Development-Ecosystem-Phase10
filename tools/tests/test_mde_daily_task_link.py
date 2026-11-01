"""D3 checks with the authentic TaskStore and loader in isolated repositories."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from mde.task.loader import load_task
from mde.task.store import TaskStore
from mde.task.types import TaskResult, utc_now
from tools import mde_daily_log, mde_daily_plan, mde_daily_task_link

SCRIPT = Path(__file__).resolve().parents[1] / "mde_daily_task_link.py"


class DailyTaskLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="mde d3 ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        for app in ("document-parser", "knowledge-viewer", "sample-project"):
            (self.root / "apps" / app).mkdir(parents=True)
        (self.root / "packages" / "mde-core").mkdir(parents=True)
        self.day = "2026-11-01"
        self.project = "document-parser"
        self.step = "DOC-PARSER-1"
        self.task_id = "TASK-D3-001"
        self.log = mde_daily_log.record_work(
            self.root,
            self.day,
            self.project,
            self.step,
            "실제 작업 기록",
            "동작 확인",
            None,
            "미검증",
        )
        self.store = TaskStore(self.root)
        self.task_file, self.result_file = self.fixture()

    def fixture(
        self, status: str = "completed", task_id: str | None = None
    ) -> tuple[Path, Path]:
        task_id = task_id or self.task_id
        source = self.store.dirs.pending / f"{task_id}.yaml"
        source.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "task": {
                        "id": task_id,
                        "type": "docs",
                        "title": "연결 검사",
                        "workflow": "docs",
                        "metadata": {"project": self.project, "step": self.step},
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        active = self.store.claim(load_task(source))
        now = utc_now()
        result = TaskResult(
            task_id=task_id,
            status=status,
            workflow="docs",
            started_at=now,
            completed_at=now,
            steps=({"command": "test.run", "status": "completed"},),
            summary="PRIVATE-SUMMARY",
            error="PRIVATE-ERROR",
        )
        result_path = (
            self.store.fail(active, result)
            if status == "failed"
            else self.store.complete(active, result)
        )
        return result_path.with_name(f"{task_id}.yaml"), result_path

    def link(self, write: bool = False, **changes) -> str:
        values = dict(
            root=self.root,
            day=self.day,
            project=self.project,
            step=self.step,
            task_id=self.task_id,
            write=write,
        )
        values.update(changes)
        return mde_daily_task_link.link_task_result(**values)

    def snapshot(self):
        return (
            {
                path.relative_to(self.root): path.read_bytes()
                for path in self.root.rglob("*")
                if path.is_file()
            },
            {
                path.relative_to(self.root)
                for path in self.root.rglob("*")
                if path.is_dir()
            },
        )

    def run_cli(self, *, write: bool = False, module: bool = False):
        entry = ["-m", "tools.mde_daily_task_link"] if module else [str(SCRIPT)]
        args = [
            sys.executable,
            *entry,
            "--root",
            str(self.root),
            "--date",
            self.day,
            "--project",
            self.project,
            "--step",
            self.step,
            "--task-id",
            self.task_id,
        ]
        if write:
            args.append("--write")
        return subprocess.run(
            args,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=20,
            check=False,
        )

    def test_preview_is_read_only_and_does_not_declare_verification(self) -> None:
        before = self.snapshot()
        output = self.link()
        self.assertIn("메타데이터 일치", output)
        self.assertIn("단계 완료 기록(검증 근거 별도)", output)
        self.assertNotIn("검증완료", output)
        self.assertNotIn("PRIVATE", output)
        self.assertEqual(self.snapshot(), before)

    def test_lookup_does_not_initialize_missing_state_directories(self) -> None:
        for folder in (
            self.store.dirs.pending,
            self.store.dirs.processing,
            self.store.dirs.failed,
        ):
            folder.rmdir()
        before = self.snapshot()
        with patch.object(
            TaskStore, "__init__", side_effect=AssertionError("constructor writes")
        ):
            self.assertIn("Task: completed", self.link())
        self.assertEqual(self.snapshot(), before)

    def test_write_adds_only_one_line_and_preserves_d1_d2_and_task_files(self) -> None:
        mde_daily_plan.register_plan(
            self.root, self.day, self.project, self.step, "계획", 120
        )
        mde_daily_log.record_work(
            self.root,
            self.day,
            self.project,
            self.step,
            "보완 작업",
            "보완 결과",
            None,
            "미검증",
            supplement=True,
        )
        before_files, before_dirs = self.snapshot()
        entry = self.link(write=True)
        after_files, after_dirs = self.snapshot()
        self.assertEqual(after_dirs, before_dirs)
        original = before_files.pop(self.log.relative_to(self.root))
        updated = after_files.pop(self.log.relative_to(self.root))
        self.assertEqual(after_files, before_files)
        self.assertEqual(
            updated.replace((entry + "\n").encode("utf-8"), b"", 1), original
        )
        self.assertIn("검증: 미검증", updated.decode("utf-8"))

    def test_duplicate_task_link_rejected_even_for_other_target(self) -> None:
        self.link(write=True)
        mde_daily_log.record_work(
            self.root,
            self.day,
            self.project,
            "DOC-PARSER-2",
            "다른 작업",
            "확인",
            None,
            "미검증",
        )
        document = yaml.safe_load(self.task_file.read_text(encoding="utf-8"))
        document["task"]["metadata"] = {}
        self.task_file.write_text(yaml.safe_dump(document), encoding="utf-8")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "이미 연결"):
            self.link(write=True, step="DOC-PARSER-2")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("TaskId:", self.link())

    def test_two_different_tasks_can_link_to_same_work_record(self) -> None:
        self.link(write=True)
        self.fixture(task_id="TASK-D3-002")
        self.link(write=True, task_id="TASK-D3-002")
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D3 연동]"), 2)

    def test_missing_actual_work_log_is_rejected(self) -> None:
        self.log.unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "D2 실제"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_wrong_or_duplicate_d2_record_is_rejected(self) -> None:
        original = self.log.read_text(encoding="utf-8")
        record = next(
            line
            for line in original.splitlines()
            if line.startswith(mde_daily_log.RECORD_PREFIX)
        )
        for content in (
            original.replace("DOC-PARSER-1", "OTHER"),
            original + record + "\n",
        ):
            with self.subTest(content=content):
                self.log.write_text(content, encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "정확히 1건"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_d2_record_in_wrong_section_is_rejected(self) -> None:
        original = self.log.read_text(encoding="utf-8")
        record = next(
            line
            for line in original.splitlines()
            if line.startswith(mde_daily_log.RECORD_PREFIX)
        )
        self.log.write_text(
            original.replace(record + "\n", "") + record + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "정확히 1건"):
            self.link(write=True)

    def test_bad_heading_layout_is_rejected_without_changes(self) -> None:
        self.log.write_bytes(self.log.read_bytes() + "\n## 기타\n".encode("utf-8"))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "표준 제목"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_app_core_project_and_input_validation(self) -> None:
        for changes in (
            {"project": "sample-project"},
            {"project": "studyhub"},
            {"step": "../escape"},
            {"task_id": "../../outside"},
            {"task_id": "TASK\n"},
            {"day": "2026-02-30"},
            {"write": "false"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.link(**changes)
        self.assertNotIn("[D3 연동]", self.log.read_text(encoding="utf-8"))

    def test_core_project_is_supported_without_d1_plan(self) -> None:
        mde_daily_log.record_work(
            self.root,
            self.day,
            "mde-core",
            "MDE-D3",
            "MDE 작업",
            "확인",
            None,
            "미검증",
        )
        document = yaml.safe_load(self.task_file.read_text(encoding="utf-8"))
        document["task"]["metadata"] = {"project_id": "mde-core", "step_id": "MDE-D3"}
        self.task_file.write_text(yaml.safe_dump(document), encoding="utf-8")
        self.assertIn(
            "메타데이터 일치", self.link(write=True, project="mde-core", step="MDE-D3")
        )

    def test_all_metadata_aliases_are_checked_and_partial_metadata_is_manual(
        self,
    ) -> None:
        original = self.task_file.read_bytes()
        for metadata, expected in (
            ({}, "사용자 지정 연결"),
            ({"project": self.project}, "사용자 지정 연결"),
            ({"step_id": self.step}, "사용자 지정 연결"),
            ({"project_id": self.project, "step_id": self.step}, "메타데이터 일치"),
            (
                {
                    "project": self.project,
                    "project_id": self.project,
                    "step": self.step,
                    "step_id": self.step,
                },
                "메타데이터 일치",
            ),
        ):
            with self.subTest(metadata=metadata):
                document = yaml.safe_load(original)
                document["task"]["metadata"] = metadata
                self.task_file.write_text(yaml.safe_dump(document), encoding="utf-8")
                self.assertIn(expected, self.link())

    def test_mismatched_or_conflicting_metadata_is_rejected(self) -> None:
        original = self.task_file.read_bytes()
        for metadata in (
            {"project": "knowledge-viewer"},
            {"step": "OTHER"},
            {"project": self.project, "project_id": "OTHER"},
            {"step": self.step, "step_id": "OTHER"},
            {"project": ""},
            {"step_id": None},
        ):
            with self.subTest(metadata=metadata):
                document = yaml.safe_load(original)
                document["task"]["metadata"] = metadata
                self.task_file.write_text(yaml.safe_dump(document), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "메타데이터"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_nonterminal_tasks_are_rejected_without_state_changes(self) -> None:
        for status in ("pending", "processing"):
            with self.subTest(status=status):
                moved = self.root / "tasks" / status / self.task_file.name
                self.task_file.rename(moved)
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "종료되지"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)
                moved.rename(self.task_file)

    def test_failed_task_and_test_state_are_not_marked_pass(self) -> None:
        self.task_file.unlink()
        self.result_file.unlink()
        self.task_file, self.result_file = self.fixture(status="failed")
        document = yaml.safe_load(self.result_file.read_bytes())
        document["result"]["steps"] = [{"command": "test.run", "status": "failed"}]
        self.result_file.write_text(yaml.safe_dump(document), encoding="utf-8")
        output = self.link(write=True)
        self.assertIn("Task: failed", output)
        self.assertIn("실패 기록", output)
        self.assertNotIn("PRIVATE", self.log.read_text(encoding="utf-8"))

    def test_test_step_failure_skipped_completed_and_absent_are_distinct(self) -> None:
        original = self.result_file.read_bytes()
        for statuses, expected in (
            (("completed",), "단계 완료 기록(검증 근거 별도)"),
            (("skipped",), "생략 기록"),
            (("failed",), "실패 기록"),
            (("completed", "skipped"), "생략 기록"),
            (("completed", "failed"), "실패 기록"),
            ((), "test.run 기록 없음"),
        ):
            with self.subTest(statuses=statuses):
                document = yaml.safe_load(original)
                document["result"]["steps"] = [
                    {"command": "test.run", "status": value} for value in statuses
                ]
                self.result_file.write_text(yaml.safe_dump(document), encoding="utf-8")
                self.assertIn(expected, self.link())

    def test_missing_result_and_json_only_request_are_rejected(self) -> None:
        self.result_file.unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Task 결과 YAML"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)
        self.task_file.unlink()
        (self.store.dirs.pending / f"{self.task_id}.json").write_text(
            "{}", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "찾지 못했습니다"):
            self.link(write=True)

    def test_result_identity_and_task_file_id_are_checked(self) -> None:
        original = self.result_file.read_bytes()
        for key, value in (
            ("task_id", "OTHER"),
            ("workflow", "feature"),
            ("status", "failed"),
        ):
            with self.subTest(key=key):
                document = yaml.safe_load(original)
                document["result"][key] = value
                self.result_file.write_text(yaml.safe_dump(document), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "식별정보"):
                    self.link(write=True)
        self.result_file.write_bytes(original)
        task = yaml.safe_load(self.task_file.read_bytes())
        task["task"]["id"] = "OTHER"
        self.task_file.write_text(yaml.safe_dump(task), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "입력 ID"):
            self.link(write=True)

    def test_non_id_task_filename_is_supported_by_real_find(self) -> None:
        renamed = self.task_file.with_name("custom-name.yaml")
        self.task_file.rename(renamed)
        self.task_file = renamed
        self.assertIn(self.task_id, self.link(write=True))

    def test_malformed_yaml_steps_and_unhashable_status_fail_cleanly(self) -> None:
        original = self.result_file.read_bytes()
        for payload in (
            b"[",
            b"\xff",
            b"[]",
            b"result: []",
            b"!!python/object/apply:os.system ['exit']",
        ):
            with self.subTest(payload=payload):
                self.result_file.write_bytes(payload)
                with self.assertRaises(ValueError):
                    self.link(write=True)
        for steps in (
            None,
            {},
            ["bad"],
            [{}],
            [{"command": "test.run", "status": ["completed"]}],
            [{"command": "test.run", "status": "PASS"}],
        ):
            with self.subTest(steps=steps):
                document = yaml.safe_load(original)
                document["result"]["steps"] = steps
                self.result_file.write_text(yaml.safe_dump(document), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_oversized_result_is_rejected(self) -> None:
        self.result_file.write_bytes(b"x" * (mde_daily_task_link.MAX_RESULT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "용량"):
            self.link(write=True)

    def test_bom_crlf_and_all_original_bytes_are_preserved(self) -> None:
        original = self.log.read_text(encoding="utf-8")
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                content = ("\ufeff" + original).replace("\n", newline).encode("utf-8")
                self.log.write_bytes(content)
                entry = self.link(write=True)
                self.assertEqual(
                    self.log.read_bytes().replace(
                        (newline + entry).encode("utf-8"), b"", 1
                    ),
                    content,
                )

    def test_existing_shared_lock_is_preserved(self) -> None:
        lock = self.log.with_suffix(".md.d1-lock")
        lock.write_text("active", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "잠금"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)
        self.assertIn(self.task_id, self.link())

    def test_atomic_write_failure_preserves_log_and_cleans_temporary_files(
        self,
    ) -> None:
        before = self.snapshot()
        with patch.object(
            mde_daily_task_link.os, "replace", side_effect=OSError("disk failure")
        ):
            with self.assertRaises(OSError):
                self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_external_log_edit_during_write_is_preserved(self) -> None:
        original = self.log.read_bytes()

        def external_edit(_):
            self.log.write_bytes(original + b"\nexternal edit\n")

        with patch.object(mde_daily_task_link.os, "fsync", external_edit):
            with self.assertRaisesRegex(ValueError, "저장 전"):
                self.link(write=True)
        self.assertEqual(self.log.read_bytes(), original + b"\nexternal edit\n")
        self.assertEqual(list(self.log.parent.glob(".mde-d3-*")), [])

    def test_changed_task_result_during_write_is_rejected(self) -> None:
        original = self.log.read_bytes()

        def change_result(_):
            self.result_file.write_bytes(
                self.result_file.read_bytes() + b"\n# changed\n"
            )

        with patch.object(mde_daily_task_link.os, "fsync", change_result):
            with self.assertRaisesRegex(ValueError, "실행 결과가 변경"):
                self.link(write=True)
        self.assertEqual(self.log.read_bytes(), original)

    def test_cli_script_module_and_duplicate_error(self) -> None:
        before = self.snapshot()
        for module in (False, True):
            result = self.run_cli(module=module)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[D3 연동]", result.stdout)
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.run_cli(write=True).returncode, 0)
        duplicate = self.run_cli(write=True)
        self.assertEqual(duplicate.returncode, 1)
        self.assertNotIn("Traceback", duplicate.stderr)

    def test_concurrent_writes_link_one_task_once(self) -> None:
        command = [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(self.root),
            "--date",
            self.day,
            "--project",
            self.project,
            "--step",
            self.step,
            "--task-id",
            self.task_id,
            "--write",
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
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D3 연동]"), 1)

    def test_symlink_result_is_rejected_before_find_can_read_it(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            source = Path(external) / "outside.yaml"
            source.write_bytes(self.result_file.read_bytes())
            self.result_file.unlink()
            try:
                self.result_file.symlink_to(source)
            except OSError:
                self.skipTest("Windows symlink creation requires additional privileges")
            self.addCleanup(self.result_file.unlink)
            with patch.object(
                TaskStore, "find", side_effect=AssertionError("must not read")
            ):
                with self.assertRaisesRegex(ValueError, "경로"):
                    self.link(write=True)


if __name__ == "__main__":
    unittest.main()
