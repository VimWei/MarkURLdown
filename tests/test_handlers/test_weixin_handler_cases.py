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
    opt.use_shared_browser = kwargs.get("use_shared_browser", True)
    return opt


@pytest.mark.unit
def test_weixin_blocked_returns_none_and_fallbacks():
    url = "https://mp.weixin.qq.com/s/abc"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with mock.patch("markitdown_app.core.registry.fetch_weixin_article") as fw, \
        mock.patch("markitdown_app.core.registry.convert_url") as gen:
        fw.return_value = mock.Mock(title="需完成验证", html_markdown="验证")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"


@pytest.mark.unit
def test_weixin_normal_content_passes():
    url = "https://mp.weixin.qq.com/s/abc"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with mock.patch("markitdown_app.core.registry.fetch_weixin_article") as fw, \
        mock.patch("markitdown_app.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t):
        fw.return_value = mock.Mock(title="WX", html_markdown="ok" * 1000)
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "WX"


