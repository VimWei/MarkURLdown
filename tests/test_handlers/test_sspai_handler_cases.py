from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.app_types import ConvertPayload, ConversionOptions
from markitdown_app.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_sspai_success_basic():
    url = "https://sspai.com/post/123"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with mock.patch("markitdown_app.core.registry.fetch_sspai_article") as fs, \
        mock.patch("markitdown_app.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t), \
        mock.patch("markitdown_app.core.registry.derive_md_filename", return_value="s.md"):
        fs.return_value = mock.Mock(title="S", html_markdown="valid content" * 200)
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "S"
    assert res.suggested_filename == "s.md"


@pytest.mark.unit
def test_sspai_too_short_fallback():
    url = "https://sspai.com/post/123"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with mock.patch("markitdown_app.core.registry.fetch_sspai_article") as fs, \
        mock.patch("markitdown_app.core.registry.convert_url") as gen:
        fs.return_value = mock.Mock(title="S", html_markdown="x" * 10)
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"


