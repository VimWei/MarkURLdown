from __future__ import annotations

import types

import pytest

from markurldown.core.handlers import zhihu_handler as zh


@pytest.mark.unit
def test_goto_target_and_prepare_content_calls_paths(monkeypatch):
    class Page:
        def __init__(self):
            self.got = False
            self.waits = []
            self.keyboard = types.SimpleNamespace(press=lambda k: None)

        def goto(self, url, wait_until="domcontentloaded", timeout=30000):
            self.got = True

        def wait_for_timeout(self, ms):
            self.waits.append(ms)

        def query_selector(self, sel):
            return None

    p = Page()
    # make try_close_modal_with_selectors return True path
    monkeypatch.setattr(zh, "try_close_modal_with_selectors", lambda *a, **k: True)
    monkeypatch.setattr(zh, "_try_click_expand_buttons", lambda page: False)
    zh._goto_target_and_prepare_content(
        p, "https://www.zhihu.com/question/1/answer/2", on_detail=lambda s: None
    )
    assert p.got and p.waits


@pytest.mark.unit
def test_fetch_zhihu_article_unknown_fallback_then_success(monkeypatch):
    # unknown URL triggers generic fallback loop: first generic returns success
    monkeypatch.setattr(
        zh._generic,
        "_try_lightweight_markitdown",
        lambda url, session: zh.CrawlerResult(success=True, title="T", text_content="ok" * 600),
    )
    r = zh.fetch_zhihu_article(session=object(), url="https://unknown.example.com/page")
    assert r.title == "T" and len(r.html_markdown) > 0
