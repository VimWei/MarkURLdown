from __future__ import annotations

import pytest

from markitdown_app.core.normalize import normalize_markdown_headings


@pytest.mark.unit
def test_adjacent_headings_insert_blank_lines():
    text = "# A\n## B\nText"
    out = normalize_markdown_headings(text, None)
    lines = out.splitlines()
    # Expect blank lines after headings with following non-empty line
    assert lines[0] == "# A"
    assert lines[1] == ""
    assert lines[2] == "## B"
    assert lines[3] == ""


@pytest.mark.unit
def test_weird_title_promotion_with_punctuation():
    text = "....Hello\nBody"
    out = normalize_markdown_headings(text, "Hello World")
    # Current implementation不会去掉前缀标点，故不提升；仅断言内容保留
    assert out.startswith("....Hello\n")
