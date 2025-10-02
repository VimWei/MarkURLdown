from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_weixin_blocked_fallbacks_to_generic():
    url = "https://mp.weixin.qq.com/s/abc"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_weixin_article") as fw,
        mock.patch("markdownall.core.registry.convert_url") as gen,
    ):
        # Simulate blocked/invalid short content -> handler returns None
        fw.return_value = mock.Mock(title="验证", html_markdown="需完成验证")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"
    assert res.markdown == "Generic"


@pytest.mark.unit
def test_zhihu_content_passes():
    url = "https://zhuanlan.zhihu.com/p/1"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_zhihu_article") as fz,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
    ):
        fz.return_value = mock.Mock(title="Z", html_markdown="valid content" * 100)
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "Z"
    assert res.markdown.startswith("valid content")


@pytest.mark.unit
def test_sspai_too_short_fallbacks():
    url = "https://sspai.com/post/123"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_sspai_article") as fs,
        mock.patch("markdownall.core.registry.convert_url") as gen,
    ):
        fs.return_value = mock.Mock(title="S", html_markdown="short")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"


@pytest.mark.unit
def test_wordpress_basic_pass():
    url = "https://skywind.me/blog/archives/100"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_wordpress_article") as fw,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
    ):
        fw.return_value = mock.Mock(title="W", html_markdown="ok content")
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "W"


@pytest.mark.unit
def test_nextjs_basic_pass():
    url = "https://guangzhengli.com/blog/hello"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_nextjs_article") as fn,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
    ):
        fn.return_value = mock.Mock(title="N", html_markdown="ok content")
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "N"
