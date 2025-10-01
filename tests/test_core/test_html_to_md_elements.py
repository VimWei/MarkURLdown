from __future__ import annotations

from unittest import mock

import pytest
from bs4 import BeautifulSoup

from markurldown.core.html_to_md import html_fragment_to_markdown


@pytest.mark.unit
def test_legacy_mappings_headings_lists_links_code_blockquote():
    html = """
    <h1>Title</h1>
    <p>para</p>
    <ul><li>item1</li><li>item2</li></ul>
    <ol><li>a</li><li>b</li></ol>
    <p><a href="https://example.com">link</a></p>
    <blockquote>quote line</blockquote>
    <pre><code>print('x')</code></pre>
    """
    root = BeautifulSoup(html, "html.parser")
    # Bypass MarkItDown path so legacy runs
    with mock.patch(
        "markitdown.converters._html_converter.HtmlConverter.convert_string",
        side_effect=RuntimeError("skip"),
    ):
        md = html_fragment_to_markdown(root)

    assert md.startswith("# Title\n\n")
    assert "- item1" in md and "- item2" in md
    assert "1. a" in md and "2. b" in md
    assert "[link](https://example.com)" in md
    assert md.count("```") == 2
    assert "> quote line" in md
