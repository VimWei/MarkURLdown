from __future__ import annotations

import json
import os
from dataclasses import asdict


def save_config(path: str, data: dict) -> None:
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
