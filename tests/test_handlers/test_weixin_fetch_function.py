from __future__ import annotations

import types

import pytest

from markitdown_app.core.handlers import weixin_handler as wx


@pytest.mark.unit
def test_fetch_weixin_article_success(monkeypatch):
    # First attempt returns success with valid content
    wxres = wx.CrawlerResult(
        success=True, title="T", text_content="<html><div>ok content</div></html>"
    )
    monkeypatch.setattr(
        wx, "_try_playwright_crawler", lambda url, on_detail=None, shared_browser=None: wxres
    )
    r = wx.fetch_weixin_article(
        session=object(), url="https://mp.weixin.qq.com/s/abc", on_detail=None, shared_browser=None
    )
    assert r.title == "T" and len((r.html_markdown or "")) >= 0


@pytest.mark.unit
def test_fetch_weixin_article_failure_raises(monkeypatch):
    # Always fail path triggering final exception
    wxres = wx.CrawlerResult(success=False, title=None, text_content="", error="e")
    monkeypatch.setattr(wx, "_try_playwright_crawler", lambda *a, **k: wxres)
    with pytest.raises(Exception):
        wx.fetch_weixin_article(session=object(), url="https://mp.weixin.qq.com/s/abc")
