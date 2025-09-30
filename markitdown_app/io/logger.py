from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable


def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _project_root() -> str:
    # Project root assumed as three levels up from this file: markitdown_app/io/logger.py -> project
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _log_dir() -> str:
    return os.path.join(_project_root(), "log")


def _daily_log_path() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_log_dir(), f"{today}.log")


def log_urls(urls: Iterable[str]) -> None:
    """Append the provided URLs into today's log file under the project-level log directory.

    Log format:
      [HH:MM:SS] url1
      [HH:MM:SS] url2
    """
    urls = list(urls)
    if not urls:
        return
    _ensure_dir(_log_dir())
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        with open(_daily_log_path(), "a", encoding="utf-8") as f:
            for u in urls:
                line = f"[{ts}] {u}\n"
                f.write(line)
    except Exception:
        # Swallow logging errors to avoid impacting main flow
        pass
