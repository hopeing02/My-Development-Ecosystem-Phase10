from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mde.task.model import TaskManifest, load_task_manifest


class ApplyError(RuntimeError):
    """Raised when applying a patch or task fails."""


@dataclass(frozen=True)
class ApplyResult:
    patch_path: Path
    target_path: Path
    backup_path: Path


@dataclass(frozen=True)
class ApplyBatchResult:
    results: list[ApplyResult]


def read_patch_file(patch_path: Path) -> str:
    if not patch_path.is_file():
        raise ApplyError(f"Patch file not found: {patch_path}")

    return patch_path.read_text(encoding="utf-8")


def create_backup(target_path: Path) -> Path:
    if not target_path.is_file():
        raise ApplyError(f"Target file not found: {target_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = target_path.with_suffix(target_path.suffix + f".bak_{timestamp}")

    shutil.copy2(target_path, backup_path)

    return backup_path


def write_target_file(target_path: Path, content: str) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")


def restore_backup(backup_path: Path, target_path: Path) -> None:
    if not backup_path.is_file():
        raise ApplyError(f"Backup file not found: {backup_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)


def remove_backup(backup_path: Path) -> None:
    if backup_path.exists():
        backup_path.unlink()


def run_pytest() -> None:
    completed = subprocess.run(
        ["uv", "run", "pytest"],
        check=False,
        text=True,
    )

    if completed.returncode != 0:
        raise ApplyError("pytest failed after applying patches.")


def apply_patch_without_tests(
    patch_path: Path,
    target_path: Path,
) -> ApplyResult:
    content = read_patch_file(patch_path)
    backup_path = create_backup(target_path)

    try:
        write_target_file(target_path, content)
    except OSError as error:
        restore_backup(backup_path, target_path)
        raise ApplyError(f"Failed to write target file: {target_path}") from error

    return ApplyResult(
        patch_path=patch_path,
        target_path=target_path,
        backup_path=backup_path,
    )


def rollback_results(results: list[ApplyResult]) -> None:
    rollback_errors: list[str] = []

    for result in reversed(results):
        try:
            restore_backup(result.backup_path, result.target_path)
        except ApplyError as error:
            rollback_errors.append(str(error))

    if rollback_errors:
        joined_errors = "; ".join(rollback_errors)
        raise ApplyError(f"Rollback failed: {joined_errors}")


def remove_backups(results: list[ApplyResult]) -> None:
    for result in results:
        remove_backup(result.backup_path)


def apply_patches(
    patch_targets: list[tuple[Path, Path]],
    run_tests: bool = True,
    keep_backups: bool = True,
) -> ApplyBatchResult:
    if not patch_targets:
        raise ApplyError("No patches were provided.")

    results: list[ApplyResult] = []

    try:
        for patch_path, target_path in patch_targets:
            result = apply_patch_without_tests(
                patch_path=patch_path,
                target_path=target_path,
            )
            results.append(result)

        if run_tests:
            run_pytest()

    except (ApplyError, OSError) as error:
        rollback_results(results)

        if isinstance(error, ApplyError):
            raise

        raise ApplyError("Failed while applying patch batch.") from error

    if not keep_backups:
        remove_backups(results)

    return ApplyBatchResult(results=results)


def apply_patch(
    patch_path: Path,
    target_path: Path,
    run_tests: bool = True,
    keep_backup: bool = True,
) -> ApplyResult:
    batch_result = apply_patches(
        patch_targets=[(patch_path, target_path)],
        run_tests=run_tests,
        keep_backups=keep_backup,
    )

    return batch_result.results[0]


def build_task_patch_targets(
    task: TaskManifest,
    project_root: Path | None = None,
) -> list[tuple[Path, Path]]:
    root = project_root or Path.cwd()

    return [
        (
            task_file.patch_path,
            root / task_file.target_path,
        )
        for task_file in task.files
    ]


def apply_task(
    manifest_path: Path,
    project_root: Path | None = None,
    run_tests: bool = True,
    keep_backups: bool = True,
) -> ApplyBatchResult:
    task = load_task_manifest(manifest_path)

    patch_targets = build_task_patch_targets(
        task,
        project_root=project_root,
    )

    return apply_patches(
        patch_targets=patch_targets,
        run_tests=run_tests,
        keep_backups=keep_backups,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply an MDE patch or task manifest.")

    parser.add_argument(
        "source",
        help="Patch file or manifest.yaml path.",
    )
    parser.add_argument(
        "--target",
        help="Target path when applying a single patch.",
    )
    parser.add_argument(
        "--no-test",
        action="store_true",
        help="Apply without running pytest.",
    )
    parser.add_argument(
        "--remove-backup",
        action="store_true",
        help="Delete backup files after successful application.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = Path(args.source)
    run_tests = not args.no_test
    keep_backups = not args.remove_backup

    try:
        if source_path.name == "manifest.yaml":
            result = apply_task(
                manifest_path=source_path,
                run_tests=run_tests,
                keep_backups=keep_backups,
            )

            print("Task applied.")
            print(f"Files applied: {len(result.results)}")

            for item in result.results:
                print(f"{item.patch_path} -> {item.target_path}")

            return 0

        if not args.target:
            parser.error("--target is required when applying a single patch.")

        result = apply_patch(
            patch_path=source_path,
            target_path=Path(args.target),
            run_tests=run_tests,
            keep_backup=keep_backups,
        )

    except ApplyError as error:
        print(error)
        return 1

    print("Patch applied.")
    print(f"Patch: {result.patch_path}")
    print(f"Target: {result.target_path}")
    print(f"Backup: {result.backup_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
