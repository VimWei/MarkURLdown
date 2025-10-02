from __future__ import annotations

import re


def normalize_markdown_headings(text: str, title: str | None) -> str:
    if not isinstance(text, str) or not text.strip():
        return text or ""

    lines = text.splitlines()

    def strip_emphasis(s: str) -> str:
        s = s.strip()
        if re.fullmatch(r"\*\*(.+)\*\*", s):
            s = re.sub(r"^\*\*(.+)\*\*$", r"\1", s)
        if re.fullmatch(r"\*(.+)\*", s):
            s = re.sub(r"^\*(.+)\*$", r"\1", s)
        return s.strip()

    cleaned: list[str] = []
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.+)$", ln)
        if m:
            hashes, content = m.group(1), m.group(2).strip()
            content = strip_emphasis(content)
            ln = f"{hashes} {content}"
        cleaned.append(ln)
    lines = cleaned

    promoted: list[str] = []
    for ln in lines:
        if re.fullmatch(r"\s*\*{2,}\s*[^*].*?\s*\*{2,}\s*", ln) and not re.match(r"^#{1,6}\s+", ln):
            content = re.sub(r"^\s*\*+\s*(.*?)\s*\*+\s*$", r"\1", ln).strip()
            promoted.append(f"## {content}")
        else:
            promoted.append(ln)
    lines = promoted

    first_idx = None
    for i, ln in enumerate(lines):
        if ln.strip():
            first_idx = i
            break

    if first_idx is not None:
        first_line = lines[first_idx]
        if not re.match(r"^#{1,6}\s+", first_line):
            candidate = strip_emphasis(first_line)
            should_promote = False
            if (title or "").strip():
                tnorm = re.sub(r"\s+", " ", title).strip()
                cnorm = re.sub(r"\s+", " ", candidate).strip()
                should_promote = (cnorm == tnorm) or (
                    len(cnorm) >= 4 and tnorm.lower().startswith(cnorm.lower())
                )
            else:
                should_promote = len(candidate) >= 4
            if should_promote:
                lines[first_idx] = f"# {candidate}"

    out: list[str] = []
    for i, ln in enumerate(lines):
        out.append(ln)
        if re.match(r"^#{1,6}\s+", ln):
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if nxt is not None and nxt.strip() != "":
                out.append("")

    result = "\n".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result).strip() + "\n"
    return result
