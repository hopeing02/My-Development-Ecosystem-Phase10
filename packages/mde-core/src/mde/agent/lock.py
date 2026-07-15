from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOCK_FILE = Path(".mde") / "agent.lock"


class LockError(RuntimeError):
    """Raised when the MDE agent lock cannot be acquired."""


@dataclass(frozen=True)
class LockInfo:
    lock_path: Path
    process_id: int
    created_at: str


def build_lock_content(process_id: int, created_at: str) -> str:
    return f"process_id={process_id}\n" f"created_at={created_at}\n"


def acquire_lock(root_dir: Path | None = None) -> LockInfo:
    root = root_dir or Path.cwd()
    lock_path = root / LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        existing_content = lock_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        raise LockError(
            "MDE agent is already running or an old lock remains: "
            f"{lock_path}\n{existing_content}"
        )

    process_id = os.getpid()
    created_at = datetime.now().isoformat(timespec="seconds")

    try:
        lock_path.write_text(
            build_lock_content(process_id, created_at),
            encoding="utf-8",
        )
    except OSError as error:
        raise LockError(f"Could not create agent lock: {lock_path}") from error

    return LockInfo(
        lock_path=lock_path,
        process_id=process_id,
        created_at=created_at,
    )


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except OSError as error:
        raise LockError(f"Could not remove agent lock: {lock_path}") from error


class AgentLock:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir
        self.info: LockInfo | None = None

    def __enter__(self) -> LockInfo:
        self.info = acquire_lock(self.root_dir)
        return self.info

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> bool:
        if self.info is not None:
            release_lock(self.info.lock_path)

        return False
