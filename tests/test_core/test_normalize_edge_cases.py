from __future__ import annotations

import pytest

from markurldown.core.normalize import normalize_markdown_headings


@pytest.mark.unit
def test_promote_first_line_matches_title():
    text = "My Article\nContent"
    out = normalize_markdown_headings(text, "My Article")
    assert out.startswith("# My Article\n\n")


@pytest.mark.unit
def test_promote_bold_line_to_h2():
    text = "** Section **\npara"
    out = normalize_markdown_headings(text, None)
    assert out.splitlines()[0].startswith("## ")


@pytest.mark.unit
def test_strip_emphasis_in_headings_and_insert_blank_line():
    text = "## **Heading**\nNext line"
    out = normalize_markdown_headings(text, None)
    lines = out.splitlines()
    assert lines[0] == "## Heading"
    # should insert a blank line after heading when next line is not empty
    assert lines[1] == ""


@pytest.mark.unit
def test_no_change_when_empty_or_non_string():
    assert normalize_markdown_headings("", None) == ""
    # Function returns the input when it's non-empty but whitespace-only; then trailing "\n" is added
    assert normalize_markdown_headings("   ", None).strip() == ""


@pytest.mark.unit
def test_title_prefix_promotion():
    # first non-heading line is a prefix of title (>=4 chars), should promote
    text = "MarkIt\nBody"
    out = normalize_markdown_headings(text, "MarkItDown")
    assert out.startswith("# MarkIt\n\n")
