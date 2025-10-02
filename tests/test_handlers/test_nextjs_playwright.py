from __future__ import annotations

import sys
import types

import pytest

from markdownall.core.handlers import nextjs_handler as nx


@pytest.mark.unit
@pytest.mark.handler
def test_nextjs_try_playwright_crawler_shared_and_independent(monkeypatch):
    # shared browser path
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
    )
    context = types.SimpleNamespace(new_page=lambda: page)
    monkeypatch.setattr(nx, "new_context_and_page", lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(nx, "read_page_content_and_title", lambda p: ("<html>OK</html>", "T"))
    monkeypatch.setattr(nx, "teardown_context_page", lambda c, p: None)
    r = nx._try_playwright_crawler("https://u", shared_browser=object())
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"

    # independent browser path via mocked sync_playwright
    class DummyPage:
        def goto(self, *a, **k):
            return None

        def wait_for_timeout(self, ms):
            return None

        def content(self):
            return "<html>OK</html>"

        def title(self):
            return "T"

    class DummyContext:
        def new_page(self):
            return DummyPage()

    class DummyBrowser:
        def new_context(self):
            return DummyContext()

        def close(self):
            return None

    class DummyP:
        def __init__(self):
            # provide instance attribute chromium with launch accepting arbitrary kwargs
            self.chromium = types.SimpleNamespace(launch=lambda **kwargs: DummyBrowser())

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_playwright_module = types.SimpleNamespace(sync_playwright=lambda: DummyP())
    # ensure clean import state
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_playwright_module)

    r2 = nx._try_playwright_crawler("https://u")
    assert r2.success and r2.html_markdown.startswith("<html>") and r2.title == "T"
