from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markdownall.core.handlers import sspai_handler as sp


@pytest.mark.unit
@pytest.mark.handler
def test_sspai_try_playwright_crawler_shared_success_and_error(monkeypatch):
    # provide a minimal playwright package to satisfy import
    class DummyP:
        def __init__(self):
            self.chromium = types.SimpleNamespace(launch=lambda **kwargs: object())

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_pkg = types.SimpleNamespace()
    fake_sync = types.SimpleNamespace(sync_playwright=lambda: DummyP())
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync)

    # success with shared browser
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
        content=lambda: "<html>OK</html>",
        title=lambda: "T",
    )
    context = types.SimpleNamespace(new_page=lambda: page, close=lambda: None)
    monkeypatch.setattr(
        sp,
        "new_context_and_page",
        lambda b, context_options=None, apply_stealth=False: (context, page),
    )
    # Mock the imported function directly in the sspai_handler module
    monkeypatch.setattr(
        sp, "read_page_content_and_title", lambda p, logger=None: ("<html>OK</html>", "T")
    )
    monkeypatch.setattr(sp, "teardown_context_page", lambda c, p: None)
    r = sp._try_playwright_crawler("https://u", shared_browser=object())
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"

    # error branch
    monkeypatch.setattr(
        sp, "new_context_and_page", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r2 = sp._try_playwright_crawler("https://u", shared_browser=object())
    assert r2.success is False


@pytest.mark.unit
@pytest.mark.handler
def test_sspai_try_playwright_crawler_independent_browser(monkeypatch):
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
        def new_context(self, **kwargs):
            return DummyContext()

        def close(self):
            return None

    class DummyP:
        def __init__(self):
            self.chromium = types.SimpleNamespace(launch=lambda **kwargs: DummyBrowser())

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_pkg = types.SimpleNamespace()
    fake_sync = types.SimpleNamespace(sync_playwright=lambda: DummyP())
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync)

    r = sp._try_playwright_crawler("https://u")
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"
