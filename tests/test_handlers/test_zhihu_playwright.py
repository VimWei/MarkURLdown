from __future__ import annotations

import sys
import types

import pytest

from markdownall.core.handlers import zhihu_handler as zh


@pytest.mark.unit
@pytest.mark.handler
def test_zhihu_try_playwright_crawler_success(monkeypatch):
    class DummyPage:
        pass

    class DummyContext:
        def __init__(self, page):
            self._page = page

    class DummyBrowser:
        def __init__(self, page):
            self._page = page

    class DummyP:
        def __init__(self, page):
            self.chromium = types.SimpleNamespace(launch=lambda **kwargs: DummyBrowser(page))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    page = DummyPage()
    monkeypatch.setattr(
        zh, "new_context_and_page", lambda b, apply_stealth=False: (DummyContext(page), page)
    )
    monkeypatch.setattr(zh, "_apply_zhihu_stealth_and_defaults", lambda p: None)
    monkeypatch.setattr(zh, "_goto_target_and_prepare_content", lambda p, url, cb=None: None)
    monkeypatch.setattr(
        zh, "read_page_content_and_title", lambda p, on_detail=None: ("<html>OK</html>", "T")
    )

    fake_sync = lambda: DummyP(page)
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=fake_sync)
    )

    r = zh._try_playwright_crawler("https://u")
    assert r.success and r.text_content.startswith("<html>") and r.title == "T"


@pytest.mark.unit
@pytest.mark.handler
def test_zhihu_try_playwright_crawler_import_error(monkeypatch):
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)

    r = zh._try_playwright_crawler("https://u")
    assert r.success is False and r.error and "Playwright" in r.error
