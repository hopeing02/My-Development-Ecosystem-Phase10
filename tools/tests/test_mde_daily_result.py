"""D2 behavior and CLI checks using the real TaskStore in temporary repositories."""

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
from tools import mde_daily_plan, mde_daily_result

SCRIPT = Path(__file__).resolve().parents[1] / "mde_daily_result.py"


class DailyResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="mde d2 ")
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
        self.day = "2026-10-30"
        self.log = mde_daily_plan.register_plan(
            self.root, self.day, "document-parser", "DOC-PARSER-1", "문서 검증", 120
        )

    def fixture(
        self,
        status: str = "completed",
        *,
        steps: tuple[dict, ...] | None = None,
        metadata: dict | None = None,
        filename: str = "TASK-001.yaml",
    ) -> tuple[Path, Path]:
        store = TaskStore(self.root)
        source = store.dirs.pending / filename
        source.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "task": {
                        "id": "TASK-001",
                        "type": "docs",
                        "title": "문서 검증",
                        "workflow": "docs",
                        "metadata": metadata or {},
                    },
                }
            ),
            encoding="utf-8",
        )
        if status == "pending":
            return source, source.with_name("TASK-001.result.yaml")
        claimed = store.claim(load_task(source))
        if status == "processing":
            return claimed.source_path, claimed.source_path.with_name(
                "TASK-001.result.yaml"
            )
        now = utc_now()
        result = TaskResult(
            task_id="TASK-001",
            status=status,
            workflow="docs",
            started_at=now,
            completed_at=now,
            steps=(
                steps
                if steps is not None
                else ({"command": "test.run", "status": "completed"},)
            ),
            summary="PRIVATE-SUMMARY",
            error="PRIVATE-ERROR" if status == "failed" else None,
        )
        result_path = (
            store.fail(claimed, result)
            if status == "failed"
            else store.complete(claimed, result)
        )
        return result_path.with_name(filename), result_path

    def link(self, write: bool = False, task_id: str = "TASK-001") -> str:
        return mde_daily_result.link_task_result(self.root, self.day, task_id, write)

    def snapshot(self) -> dict[Path, bytes]:
        return {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def run_cli(
        self, *args: str, module: bool = False
    ) -> subprocess.CompletedProcess[str]:
        entry = ["-m", "tools.mde_daily_result"] if module else [str(SCRIPT)]
        return subprocess.run(
            [
                sys.executable,
                *entry,
                "--root",
                str(self.root),
                "--date",
                self.day,
                *args,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=20,
            check=False,
        )

    def test_preview_then_one_write_preserves_plan_and_tasks(self) -> None:
        self.fixture(metadata={"project": "document-parser"})
        before = self.snapshot()
        plan = mde_daily_plan.show_plan(self.root, self.day)
        entry = self.link()
        self.assertEqual(self.snapshot(), before)
        self.assertIn("test.run 기록상 완료", entry)
        self.assertNotIn("PRIVATE", entry)
        self.assertEqual(self.link(write=True), entry)
        after = self.snapshot()
        original_log = before.pop(self.log.relative_to(self.root))
        updated = after.pop(self.log.relative_to(self.root))
        self.assertEqual(before, after)
        self.assertEqual(
            updated.replace((entry + "\n").encode("utf-8"), b"", 1), original_log
        )
        self.assertEqual(mde_daily_plan.show_plan(self.root, self.day), plan)
        with self.assertRaisesRegex(ValueError, "이미 D2"):
            self.link(write=True)
        self.assertEqual(self.log.read_bytes(), updated)
        self.assertEqual(self.link(), entry)

    def test_verification_comes_from_all_recorded_test_steps(self) -> None:
        _, result = self.fixture()
        for statuses, expected in (
            (("completed",), "test.run 기록상 완료"),
            (("failed",), "test.run 실패"),
            (("skipped",), "test.run 생략"),
            (("completed", "skipped"), "test.run 일부 생략"),
            (("completed", "failed"), "test.run 실패"),
            ((), "test.run 결과 없음"),
        ):
            with self.subTest(statuses=statuses):
                document = yaml.safe_load(result.read_text(encoding="utf-8"))
                document["result"]["steps"] = [
                    {"command": "test.run", "status": status} for status in statuses
                ] + [{"command": "doc.generate", "status": "completed"}]
                result.write_text(yaml.safe_dump(document), encoding="utf-8")
                self.assertIn(expected, self.link())

    def test_failed_task_stays_failed_and_does_not_copy_error_text(self) -> None:
        self.fixture(
            status="failed", steps=({"command": "test.run", "status": "failed"},)
        )
        before = self.snapshot()
        entry = self.link(write=True)
        self.assertIn("Task: failed", entry)
        self.assertIn("test.run 실패", entry)
        self.assertNotIn("PRIVATE", self.log.read_text(encoding="utf-8"))
        for name, content in before.items():
            if name != self.log.relative_to(self.root):
                self.assertEqual((self.root / name).read_bytes(), content)

    def test_metadata_project_id_and_missing_metadata_are_supported(self) -> None:
        task, _ = self.fixture()
        for metadata in (
            {},
            {"project": "document-parser"},
            {"project_id": "document-parser"},
            {"project": "document-parser", "project_id": "document-parser"},
        ):
            with self.subTest(metadata=metadata):
                doc = yaml.safe_load(task.read_text(encoding="utf-8"))
                doc["task"]["metadata"] = metadata
                task.write_text(yaml.safe_dump(doc), encoding="utf-8")
                self.assertIn("Task: completed", self.link())

    def test_conflicting_project_metadata_is_rejected(self) -> None:
        task, _ = self.fixture()
        for metadata in (
            {"project": "knowledge-viewer"},
            {"project_id": "knowledge-viewer"},
            {"project": "document-parser", "project_id": "knowledge-viewer"},
            {"project": ""},
            {"project_id": 0},
        ):
            with self.subTest(metadata=metadata):
                doc = yaml.safe_load(task.read_text(encoding="utf-8"))
                doc["task"]["metadata"] = metadata
                task.write_text(yaml.safe_dump(doc), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "프로젝트가"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_nonterminal_tasks_are_rejected(self) -> None:
        for status in ("pending", "processing"):
            with self.subTest(status=status):
                task, _ = self.fixture(status)
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "아직 종료"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)
                task.unlink()

    def test_w1_json_is_not_a_taskstore_yaml_task(self) -> None:
        pending = self.root / "tasks" / "pending"
        pending.mkdir(parents=True)
        (pending / "TASK-001.json").write_text(
            '{"taskId":"TASK-001"}', encoding="utf-8"
        )
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "찾지 못했습니다"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_missing_plan_is_rejected_before_taskstore_creation(self) -> None:
        self.log.unlink()
        with self.assertRaisesRegex(ValueError, "D1 개발계획"):
            self.link(write=True)
        self.assertFalse((self.root / "tasks").exists())
        self.assertFalse(self.log.exists())

    def test_multiple_or_unknown_app_plans_are_rejected(self) -> None:
        original = self.log.read_bytes()
        for content in (
            original
            + mde_daily_plan.show_plan(self.root, self.day).encode("utf-8")
            + b"\n",
            original.replace(b"document-parser", b"sample-project"),
            original.replace(b"document-parser", b"unknown-project"),
        ):
            with self.subTest(content=content):
                self.log.write_bytes(content)
                with self.assertRaises(ValueError):
                    self.link(write=True)
                self.assertEqual(self.log.read_bytes(), content)
                self.assertFalse((self.root / "tasks").exists())

    def test_invalid_dates_and_ids_do_not_create_taskstore(self) -> None:
        for day, task_id in (
            ("2026-02-29", "TASK-001"),
            ("../outside", "TASK-001"),
            (self.day, "../../escape"),
            (self.day, "TASK-001\n"),
            (self.day, ""),
            (self.day, "T" * 65),
        ):
            with self.subTest(day=day, task_id=task_id), self.assertRaises(ValueError):
                mde_daily_result.link_task_result(self.root, day, task_id, True)
        self.assertFalse((self.root / "tasks").exists())

    def test_truthy_write_value_does_not_enable_writes(self) -> None:
        for write in ("false", 1, None):
            with self.subTest(write=write), self.assertRaises(ValueError):
                mde_daily_result.link_task_result(
                    self.root, self.day, "TASK-001", write
                )
        self.assertFalse((self.root / "tasks").exists())

    def test_missing_result_is_not_recorded_as_completed(self) -> None:
        _, result = self.fixture()
        result.unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "YAML이 없습니다"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_task_yaml_id_must_match_requested_id(self) -> None:
        task, _ = self.fixture()
        document = yaml.safe_load(task.read_text(encoding="utf-8"))
        document["task"]["id"] = "ANOTHER-ID"
        task.write_text(yaml.safe_dump(document), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "작업 ID.*불일치"):
            self.link(write=True)
        self.assertNotIn("[D2 결과]", self.log.read_text(encoding="utf-8"))

    def test_taskstore_filename_alias_is_supported(self) -> None:
        task, result = self.fixture(filename="stored-under-another-name.yaml")
        self.assertNotEqual(task.stem, "TASK-001")
        self.assertEqual(result.name, "TASK-001.result.yaml")
        self.assertIn("`TASK-001`", self.link(write=True))

    def test_result_id_status_and_workflow_must_match(self) -> None:
        _, result = self.fixture()
        original = result.read_bytes()
        for key, value in (
            ("task_id", "ANOTHER"),
            ("status", "failed"),
            ("workflow", "feature"),
        ):
            with self.subTest(key=key):
                document = yaml.safe_load(original)
                document["result"][key] = value
                result.write_text(yaml.safe_dump(document), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "불일치"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_malformed_result_documents_do_not_touch_log(self) -> None:
        _, result = self.fixture()
        original_log = self.log.read_bytes()
        for content in (
            b"[",
            b"\xff",
            b"[]",
            b"result: []",
            b"result: null",
            b"!!python/object/apply:os.system ['exit']",
        ):
            with self.subTest(content=content):
                result.write_bytes(content)
                with self.assertRaises(ValueError):
                    self.link(write=True)
                self.assertEqual(self.log.read_bytes(), original_log)

    def test_large_results_are_rejected(self) -> None:
        _, result = self.fixture()
        result.write_bytes(b"x" * (mde_daily_result.MAX_RESULT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "너무 큽니다"):
            self.link(write=True)

    def test_invalid_steps_and_unknown_status_are_rejected(self) -> None:
        _, result = self.fixture()
        original = result.read_bytes()
        for steps in (
            {},
            None,
            ["completed"],
            [{}],
            [{"command": "test.run", "status": "passed"}],
            [{"command": "test.run", "status": ["completed"]}],
            [{"command": None, "status": "completed"}],
        ):
            with self.subTest(steps=steps):
                document = yaml.safe_load(original)
                document["result"]["steps"] = steps
                result.write_text(yaml.safe_dump(document), encoding="utf-8")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "단계 목록"):
                    self.link(write=True)
                self.assertEqual(self.snapshot(), before)

    def test_bom_crlf_blank_lines_and_five_headings_are_preserved(self) -> None:
        self.fixture()
        original = self.log.read_text(encoding="utf-8")
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                source = ("\ufeff" + original).replace("\n", newline).encode("utf-8")
                self.log.write_bytes(source)
                entry = self.link(write=True)
                self.assertEqual(
                    self.log.read_bytes().replace(
                        (newline + entry).encode("utf-8"), b"", 1
                    ),
                    source,
                )

    def test_missing_today_heading_refuses_write(self) -> None:
        self.fixture()
        self.log.write_bytes(
            self.log.read_bytes().replace(
                "## 오늘 작업".encode("utf-8"), b"# missing-section"
            )
        )
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "제목이 없습니다"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_existing_d1_lock_is_preserved(self) -> None:
        self.fixture()
        lock = self.log.with_suffix(".md.d1-lock")
        lock.write_text("active", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "잠금"):
            self.link(write=True)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("Task: completed", self.link())

    def test_replace_failure_preserves_log_and_removes_temporary_files(self) -> None:
        self.fixture()
        before = self.snapshot()
        with patch.object(
            mde_daily_result.os, "replace", side_effect=OSError("disk error")
        ):
            with self.assertRaises(OSError):
                self.link(write=True)
        self.assertEqual(self.snapshot(), before)

    def test_changed_plan_is_rechecked_before_write(self) -> None:
        self.fixture()
        original_find = TaskStore.find

        def find_and_change_plan(store: TaskStore, task_id: str):
            located = original_find(store, task_id)
            self.log.write_text(
                self.log.read_text(encoding="utf-8").replace("문서 검증", "다른 목표"),
                encoding="utf-8",
            )
            return located

        with patch.object(TaskStore, "find", find_and_change_plan):
            with self.assertRaisesRegex(ValueError, "조회 이후 변경"):
                self.link(write=True)
        self.assertIn("다른 목표", self.log.read_text(encoding="utf-8"))
        self.assertNotIn("[D2 결과]", self.log.read_text(encoding="utf-8"))

    def test_cli_script_and_package_entry_points(self) -> None:
        self.fixture()
        before = self.snapshot()
        for module in (False, True):
            with self.subTest(module=module):
                result = self.run_cli("--task-id", "TASK-001", module=module)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("test.run 기록상 완료", result.stdout)
                self.assertEqual(self.snapshot(), before)
        result = self.run_cli("--task-id", "TASK-001", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        duplicate = self.run_cli("--task-id", "TASK-001", "--write")
        self.assertEqual(duplicate.returncode, 1)
        self.assertNotIn("Traceback", duplicate.stderr)

    def test_cli_bad_task_yaml_reports_error_without_traceback(self) -> None:
        task, _ = self.fixture()
        task.write_text("task: []", encoding="utf-8")
        before = self.snapshot()
        result = self.run_cli("--task-id", "TASK-001", "--write")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_concurrent_writers_record_one_result(self) -> None:
        self.fixture()
        command = [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(self.root),
            "--date",
            self.day,
            "--task-id",
            "TASK-001",
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
        self.assertEqual(sum(p.returncode == 0 for p in processes), 1)
        self.assertEqual(self.log.read_text(encoding="utf-8").count("[D2 결과]"), 1)
        self.assertEqual(list(self.log.parent.glob("*.d1-lock")), [])

    def test_taskstore_creation_cannot_follow_external_directory_link(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            link = self.root / "tasks"
            try:
                link.symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("Windows symlink creation requires additional privileges")
            self.addCleanup(link.unlink)
            with self.assertRaisesRegex(ValueError, "저장소 밖"):
                self.link()
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_result_file_cannot_follow_external_link(self) -> None:
        _, result = self.fixture()
        with tempfile.TemporaryDirectory() as external:
            source = Path(external) / result.name
            source.write_bytes(result.read_bytes())
            result.unlink()
            try:
                result.symlink_to(source)
            except OSError:
                self.skipTest("Windows symlink creation requires additional privileges")
            self.addCleanup(result.unlink)
            with self.assertRaisesRegex(ValueError, "상태 폴더 밖"):
                self.link(write=True)
            self.assertNotIn("[D2 결과]", self.log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
