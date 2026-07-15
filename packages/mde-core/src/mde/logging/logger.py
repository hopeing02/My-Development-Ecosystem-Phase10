from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")


def build_log_path(
    prefix: str = "agent",
    root_dir: Path | None = None,
) -> Path:
    root = root_dir or Path.cwd()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    return root / LOG_DIR / f"{prefix}-{timestamp}.log"


def create_logger(
    name: str,
    log_path: Path,
) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def close_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
