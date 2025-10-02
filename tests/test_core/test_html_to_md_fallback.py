from __future__ import annotations

from unittest import mock

import pytest
from bs4 import BeautifulSoup

from markdownall.core.html_to_md import html_fragment_to_markdown


@pytest.mark.unit
def test_html_fragment_to_markdown_uses_markitdown_on_success():
    html = "<h1>Title</h1><p>Hello</p>"
    with mock.patch("markitdown.converters._html_converter.HtmlConverter") as MockConv:
        instance = MockConv.return_value
        instance.convert_string.return_value = mock.Mock(markdown="# Title\n\nHello\n")
        md = html_fragment_to_markdown(html)
        assert md == "# Title\n\nHello\n"
        instance.convert_string.assert_called_once()


@pytest.mark.unit
def test_html_fragment_to_markdown_fallbacks_on_exception():
    # Force HtmlConverter to raise to trigger legacy fallback
    html = "<h1>标题</h1><p>内容</p>"
    root = BeautifulSoup(html, "html.parser")
    with mock.patch(
        "markitdown.converters._html_converter.HtmlConverter.convert_string",
        side_effect=RuntimeError("boom"),
    ):
        md = html_fragment_to_markdown(root)
        # legacy converter should still produce heading and paragraph with trailing newline
        assert md.startswith("# ")
        assert "内容" in md
        assert md.endswith("\n")
