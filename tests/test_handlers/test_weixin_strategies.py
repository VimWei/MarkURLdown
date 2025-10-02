from __future__ import annotations

import sys
import types

import pytest

from markdownall.core.handlers import weixin_handler as wx


@pytest.mark.unit
def test_weixin_try_playwright_crawler_success_shared(monkeypatch):
    # ensure import of sync_playwright doesn't touch real playwright
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

    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
    )
    context = types.SimpleNamespace(new_page=lambda: page)
    monkeypatch.setattr(wx, "new_context_and_page", lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(
        wx, "read_page_content_and_title", lambda p, on_detail=None: ("<html>OK</html>", "T")
    )
    r = wx._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r.success and r.text_content.startswith("<html>")


@pytest.mark.unit
def test_weixin_try_playwright_crawler_import_error(monkeypatch):
    # Force ImportError path by patching sync_playwright import to raise
    def bad_import(*a, **k):
        raise ImportError("no playwright")

    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=bad_import)
    )
    r = wx._try_playwright_crawler("https://u", on_detail=None, shared_browser=None)
    assert r.success is False and "Playwright" in (r.error or "")
