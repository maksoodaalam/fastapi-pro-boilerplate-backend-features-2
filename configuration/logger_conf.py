
from __future__ import annotations

import logging
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"

_configured = False
_file_logger_paths: set[str] = set()


def configure_logging(level: int | str | None = "INFO") -> None:
    global _configured

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(name)


def get_file_logger(filename: str) -> logging.Logger:
    """Return a logger that writes to ``logs/<filename>`` at the project root (filename only, no path)."""
    if not _configured:
        configure_logging()
        logger = get_logger("T")
    else:
        logger = get_logger("T")

    safe_name = Path(filename).name
    stem = Path(safe_name).stem
    log_path = (_LOGS_DIR / safe_name).resolve()
    key = str(log_path)

    # logger = logging.getLogger()

    if key not in _file_logger_paths:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(fh)
        _file_logger_paths.add(key)

    return logger
