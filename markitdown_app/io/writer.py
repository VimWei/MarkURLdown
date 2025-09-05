from __future__ import annotations

import os


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def write_markdown(out_dir: str, filename: str, content: str) -> str:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


