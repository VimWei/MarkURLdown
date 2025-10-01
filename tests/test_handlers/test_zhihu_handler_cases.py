from __future__ import annotations

import types
from unittest import mock

import pytest

from markurldown.core.handlers import zhihu_handler as zh


@pytest.mark.unit
def test_fetch_zhihu_article_unknown_type_falls_back_to_generic(
    mock_session, mock_zhihu_url, monkeypatch
):
    # Force page type to unknown
    monkeypatch.setattr(
        zh, "_detect_zhihu_page_type", lambda url: zh.ZhihuPageType(False, False, "unknown")
    )

    # First generic strategy returns success
    ok = types.SimpleNamespace(success=True, title="T", text_content="CONTENT")
    monkeypatch.setattr(zh._generic, "_try_lightweight_markitdown", lambda url, session: ok)
    monkeypatch.setattr(
        zh._generic,
        "_try_enhanced_markitdown",
        lambda url, session: types.SimpleNamespace(success=False, title=None, text_content=""),
    )
    monkeypatch.setattr(
        zh._generic,
        "_try_direct_httpx",
        lambda url, session: types.SimpleNamespace(success=False, title=None, text_content=""),
    )

    r = zh.fetch_zhihu_article(mock_session, mock_zhihu_url)
    assert r.html_markdown == "CONTENT"


@pytest.mark.unit
def test_fetch_zhihu_article_retries_then_success(mock_session, mock_zhihu_url, monkeypatch):
    # Known page type; bypass unknown fallback
    monkeypatch.setattr(
        zh, "_detect_zhihu_page_type", lambda url: zh.ZhihuPageType(False, True, "column")
    )

    seq = [
        types.SimpleNamespace(success=False, title=None, text_content=""),
        types.SimpleNamespace(
            success=True,
            title="Hint",
            text_content="<html><h1>X</h1><article><p>" + ("x" * 1200) + "</p></article></html>",
        ),
    ]

    def _try(url, on_detail=None, shared_browser=None):
        return seq.pop(0)

    monkeypatch.setattr(zh, "_try_playwright_crawler", _try)

    # speed up retries
    with mock.patch("time.sleep", lambda *a, **k: None):
        r = zh.fetch_zhihu_article(mock_session, mock_zhihu_url)

    assert r.title is not None and r.html_markdown


@pytest.mark.unit
def test_fetch_zhihu_article_detects_validation_and_exhausts(
    mock_session, mock_zhihu_url, monkeypatch
):
    monkeypatch.setattr(
        zh, "_detect_zhihu_page_type", lambda url: zh.ZhihuPageType(False, True, "column")
    )

    # Always returns short content with validation keywords
    html = "<html><h1>验证</h1><article><p>验证</p></article></html>"
    monkeypatch.setattr(
        zh,
        "_try_playwright_crawler",
        lambda url, on_detail=None, shared_browser=None: types.SimpleNamespace(
            success=True, title="验证", text_content=html
        ),
    )

    with mock.patch("time.sleep", lambda *a, **k: None):
        with pytest.raises(Exception):
            zh.fetch_zhihu_article(mock_session, mock_zhihu_url)


from unittest import mock

import pytest

from markurldown.app_types import ConversionOptions, ConvertPayload
from markurldown.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", True)
    return opt


@pytest.mark.unit
def test_zhihu_blocked_returns_none_and_fallbacks():
    url = "https://zhuanlan.zhihu.com/p/1"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markurldown.core.registry.fetch_zhihu_article") as fz,
        mock.patch("markurldown.core.registry.convert_url") as gen,
    ):
        fz.return_value = mock.Mock(title="验证", html_markdown="登录 403 页面不存在")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"


@pytest.mark.unit
def test_zhihu_normal_content_passes():
    url = "https://zhuanlan.zhihu.com/p/1"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markurldown.core.registry.fetch_zhihu_article") as fz,
        mock.patch(
            "markurldown.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
    ):
        fz.return_value = mock.Mock(title="ZH", html_markdown="ok" * 1000)
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "ZH"
