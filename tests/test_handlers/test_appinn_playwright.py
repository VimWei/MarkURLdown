from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markdownall.core.handlers import appinn_handler as app


@pytest.mark.unit
@pytest.mark.handler
def test_appinn_try_playwright_crawler_shared_success_and_error(monkeypatch):
    # happy path with shared_browser
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
        content=lambda: "<html>OK</html>",
        title=lambda: "T",
    )
    context = types.SimpleNamespace(new_page=lambda: page, close=lambda: None)
    monkeypatch.setattr(app, "new_context_and_page", lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(app, "read_page_content_and_title", lambda p: ("<html>OK</html>", "T"))
    monkeypatch.setattr(app, "teardown_context_page", lambda c, p: None)
    r = app._try_playwright_crawler("https://u", shared_browser=object())
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"

    # error path raised from new_context_and_page
    monkeypatch.setattr(
        app, "new_context_and_page", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r2 = app._try_playwright_crawler("https://u", shared_browser=object())
    assert r2.success is False


@pytest.mark.unit
@pytest.mark.handler
def test_appinn_try_playwright_crawler_independent_browser(monkeypatch):
    # mock sync_playwright context manager and chromium launch
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
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        class chromium:
            @staticmethod
            def launch(headless=True):
                return DummyBrowser()

    # install fake playwright module into sys.modules to satisfy import
    fake_playwright_module = types.SimpleNamespace(sync_playwright=lambda: DummyP())
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_playwright_module)

    r = app._try_playwright_crawler("https://u")
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"
