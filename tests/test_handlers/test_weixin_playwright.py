from __future__ import annotations

import sys
import types

import pytest

from markdownall.core.handlers import weixin_handler as wx


@pytest.mark.unit
@pytest.mark.handler
def test_weixin_try_playwright_crawler_success(monkeypatch):
    # Prepare dummy playwright environment that matches weixin handler path
    class DummyPage:
        def wait_for_timeout(self, ms):
            return None

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
        wx, "new_context_and_page", lambda b, context_options=None, apply_stealth=False: (DummyContext(page), page)
    )
    monkeypatch.setattr(wx, "_goto_target_and_prepare_content", lambda p, url, logger=None, should_stop=None: None)
    monkeypatch.setattr(
        wx, "read_page_content_and_title", lambda p, logger=None: ("<html>OK</html>", "T")
    )

    fake_sync = lambda: DummyP(page)
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)
    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=fake_sync)
    )

    r = wx._try_playwright_crawler("https://u")
    assert r.success and r.text_content.startswith("<html>") and r.title == "T"


@pytest.mark.unit
@pytest.mark.handler
def test_weixin_try_playwright_crawler_import_error(monkeypatch):
    # Ensure ImportError pathway returns expected error shape by purging modules
    for mod in ["playwright", "playwright.sync_api"]:
        sys.modules.pop(mod, None)

    r = wx._try_playwright_crawler("https://u")
    assert r.success is False and r.error and "Playwright" in r.error
