from __future__ import annotations

import sys
import types

import pytest

from markdownall.core.handlers import wordpress_handler as wp


@pytest.mark.unit
@pytest.mark.handler
def test_wordpress_try_playwright_crawler_independent_browser(monkeypatch):
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

    fake_playwright_module = types.SimpleNamespace(sync_playwright=lambda: DummyP())
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_playwright_module)

    r = wp._try_playwright_crawler("https://u")
    assert r.success and r.html_markdown.startswith("<html>") and r.title == "T"
