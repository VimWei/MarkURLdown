from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.registry import GENERIC_HANDLER_NAME, convert


def make_opts(**kwargs) -> ConversionOptions:
    # Minimal options object; use a simple Mock with expected attributes
    opt = mock.Mock()
    # default flags
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    opt.handler_override = kwargs.get("handler_override")
    return opt


@pytest.mark.unit
def test_convert_uses_specific_handler_when_matched():
    payload = ConvertPayload(kind="url", value="https://mp.weixin.qq.com/s/abc", meta={})
    session = mock.Mock()

    # Patch in registry namespace (symbols imported into registry)
    with (
        mock.patch("markdownall.core.registry.fetch_weixin_article") as fw,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
        mock.patch("markdownall.core.registry.derive_md_filename", return_value="file.md"),
    ):
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
    with (
        mock.patch("markdownall.core.registry.fetch_appinn_article", side_effect=Exception("skip")),
        mock.patch("markdownall.core.registry.fetch_weixin_article", side_effect=Exception("skip")),
        mock.patch("markdownall.core.registry.fetch_zhihu_article", side_effect=Exception("skip")),
        mock.patch(
            "markdownall.core.registry.fetch_wordpress_article", side_effect=Exception("skip")
        ),
        mock.patch("markdownall.core.registry.fetch_nextjs_article", side_effect=Exception("skip")),
        mock.patch("markdownall.core.registry.fetch_sspai_article", side_effect=Exception("skip")),
        mock.patch("markdownall.core.registry.convert_url") as generic_conv,
    ):
        generic_conv.return_value = mock.Mock(
            title="G", markdown="Generic", suggested_filename="g.md"
        )
        res = convert(payload, session, make_opts())

    assert res.title == "G"
    assert res.markdown == "Generic"
    assert res.suggested_filename == "g.md"


@pytest.mark.unit
def test_convert_respects_forced_handler_even_without_pattern():
    payload = ConvertPayload(kind="url", value="https://example.com/post", meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_wordpress_article") as fw,
        mock.patch("markdownall.core.registry.normalize_markdown_headings", side_effect=lambda t, x: t),
        mock.patch("markdownall.core.registry.derive_md_filename", return_value="forced.md"),
        mock.patch("markdownall.core.registry._is_wordpress_site", return_value=False),
    ):
        fw.return_value = mock.Mock(title="Forced", html_markdown="WP Body")
        res = convert(payload, session, make_opts(handler_override="WordPressHandler"))

    assert res.title == "Forced"
    assert res.markdown == "WP Body"
    assert res.suggested_filename == "forced.md"


@pytest.mark.unit
def test_convert_forced_generic_skips_special_handlers():
    payload = ConvertPayload(kind="url", value="https://mp.weixin.qq.com/s/abc", meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.convert_url") as generic_conv,
        mock.patch("markdownall.core.registry.fetch_weixin_article") as weixin_handler,
    ):
        generic_conv.return_value = mock.Mock(
            title="Generic", markdown="Fallback", suggested_filename="generic.md"
        )
        res = convert(payload, session, make_opts(handler_override=GENERIC_HANDLER_NAME))

    generic_conv.assert_called_once()
    weixin_handler.assert_not_called()
    assert res.title == "Generic"
    assert res.markdown == "Fallback"
