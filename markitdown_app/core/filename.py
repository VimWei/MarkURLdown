from __future__ import annotations

import os
import re
from datetime import datetime
from urllib.parse import urlparse


def sanitize_filename(name: str, fallback: str = "untitled") -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]", "_", name or "").strip()
    return sanitized or fallback


def derive_md_filename(title: str | None, url: str, now: datetime | None = None) -> str:
    base = (title or "").strip()
    if not base:
        parsed = urlparse(url)
        base = (parsed.path.rsplit("/", 1)[-1] or parsed.netloc or "page")
    base = sanitize_filename(base)

    current = now or datetime.now()
    timestamp = current.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{base}.md"


