from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path


def save_config(path: str, data: dict) -> None:
    # Ensure parent directory exists before writing
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_from_root(root_dir: str, filename: str) -> dict:
    """Load optional json at project root; return {} if missing."""
    settings_path = os.path.join(root_dir, filename)
    if not os.path.isfile(settings_path):
        return {}
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def to_project_relative_path(path: str, project_root: str) -> str:
    """Convert an absolute path under project root to a portable root-relative string.

    Rules:
    - If the path is inside project_root, return "/" + relative_posix_path (e.g. "/data/output/sspai").
    - If the path is outside project_root or not absolute, return the original path unchanged.
    - Normalizes separators to forward slashes for portability in JSON.
    """
    if not path:
        return path
    try:
        abs_path = os.path.abspath(path)
        root = os.path.abspath(project_root)
        # Ensure we only relativize when inside project root
        try:
            rel = os.path.relpath(abs_path, root)
        except ValueError:
            # Different drives on Windows or other relpath issues → keep original
            return path
        # If path escapes root, keep original
        if rel.startswith(".."):
            return path
        # Use POSIX-style for JSON
        rel_posix = rel.replace("\\", "/")
        return "/" + rel_posix.lstrip("/")
    except Exception:
        return path


def resolve_project_path(stored: str, project_root: str) -> str:
    """Resolve a stored path to an absolute path based on project root.

    Rules:
    - If it starts with "/", treat it as project-root-relative and join with project_root.
    - If it is a plain relative path (no drive and not starting with path sep), also resolve from project_root.
    - Otherwise (absolute path), return as-is.
    """
    if not stored:
        return stored
    # Normalize for checks
    s = stored.strip()
    # Project-root relative stored form ("/data/output/...")
    if s.startswith("/"):
        joined = os.path.join(project_root, s.lstrip("/"))
        return os.path.abspath(joined)
    # If it's an absolute path already, return it
    p = Path(s)
    if p.is_absolute():
        return str(p)
    # Otherwise treat as path relative to project root
    return os.path.abspath(os.path.join(project_root, s))
