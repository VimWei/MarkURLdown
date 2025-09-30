from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.app_types import ConvertPayload, ConversionOptions
from markitdown_app.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    # Minimal options object; use a simple Mock with expected attributes
    opt = mock.Mock()
    # default flags
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_convert_uses_specific_handler_when_matched():
    payload = ConvertPayload(kind="url", value="https://mp.weixin.qq.com/s/abc", meta={})
    session = mock.Mock()

    # Patch in registry namespace (symbols imported into registry)
    with mock.patch("markitdown_app.core.registry.fetch_weixin_article") as fw, \
        mock.patch("markitdown_app.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t), \
        mock.patch("markitdown_app.core.registry.derive_md_filename", return_value="file.md"):
        fw.return_value = mock.Mock(title="T", html_markdown="Body")
        res = convert(payload, session, make_opts(download_images=False))
    assert res.title == "T"
    assert res.markdown.strip() == "Body"
    assert res.suggested_filename == "file.md"


@pytest.mark.unit
def test_convert_fallbacks_to_generic_when_handlers_return_none():
    payload = ConvertPayload(kind="url", value="https://unknown.example.com/p/1", meta={})
    session = mock.Mock()

    # Force all handlers to return None by mocking functions in registry namespace
    with mock.patch("markitdown_app.core.registry.fetch_appinn_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.fetch_weixin_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.fetch_zhihu_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.fetch_wordpress_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.fetch_nextjs_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.fetch_sspai_article", side_effect=Exception("skip")), \
        mock.patch("markitdown_app.core.registry.convert_url") as generic_conv:
        generic_conv.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"
    assert res.markdown == "Generic"
    assert res.suggested_filename == "g.md"
