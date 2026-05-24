"""
logging_config.py
=================
Centralised logging setup for the Authorised Capital Changes pipeline.

Call `configure_logging()` once at the application entry-point
(run_pipeline.py or api/main.py).  Every subsequent `logging.getLogger(__name__)`
call in any node or service will automatically write to both the terminal
and the rotating log file.

Log file location: <project_root>/data/logs/pipeline_<YYYY-MM-DD>.log
A new file is started each calendar day; up to 30 daily files are kept.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_log_dir() -> Path:
    """Return the absolute path to the log directory, creating it if needed."""
    # Anchored at the project root (two levels up from this file)
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def configure_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    run_id: str | None = None,
) -> logging.Logger:
    """
    Configure the root logger with:
      - StreamHandler  → terminal (stdout)
      - TimedRotatingFileHandler → data/logs/pipeline_<date>.log
                                   (rotates daily, keeps 30 files)

    Args:
        level:       Minimum log level (default: INFO).
        log_to_file: Set False to suppress file output (e.g. during unit tests).
        run_id:      Optional run identifier injected into every log record
                     via a LoggerAdapter; returned as a child logger.

    Returns:
        The root logger (or a LoggerAdapter if run_id is provided).
    """
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers on repeated calls (e.g. uvicorn reload)
    if root_logger.handlers:
        return _wrap_with_run_id(root_logger, run_id)

    root_logger.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Terminal handler ---------------------------------------------------
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(fmt)
    root_logger.addHandler(stream_handler)

    # --- File handler -------------------------------------------------------
    if log_to_file:
        log_dir = get_log_dir()
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = log_dir / f"pipeline_{today}.log"

        file_handler = TimedRotatingFileHandler(
            filename=str(log_path),
            when="midnight",        # rotate at midnight
            interval=1,            # every 1 day
            backupCount=30,        # keep 30 daily files
            encoding="utf-8",
            utc=False,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        file_handler.suffix = "%Y-%m-%d"  # appended to rotated filenames
        root_logger.addHandler(file_handler)

        root_logger.info(
            "Logging initialised | file=%s | level=%s",
            log_path,
            logging.getLevelName(level),
        )

    return _wrap_with_run_id(root_logger, run_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wrap_with_run_id(
    logger: logging.Logger,
    run_id: str | None,
) -> logging.Logger | logging.LoggerAdapter:
    """Wrap logger in a LoggerAdapter that prepends run_id to every message."""
    if not run_id:
        return logger
    return logging.LoggerAdapter(logger, extra={"run_id": run_id})
