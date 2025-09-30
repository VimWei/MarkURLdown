from __future__ import annotations

import types
import pytest

from markitdown_app.core.handlers import weixin_handler as wx
import sys


@pytest.mark.unit
def test_weixin_try_playwright_crawler_success_shared(monkeypatch):
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
    )
    context = types.SimpleNamespace(new_page=lambda: page)
    monkeypatch.setattr(wx, 'new_context_and_page', lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(wx, 'read_page_content_and_title', lambda p, on_detail=None: ("<html>OK</html>", "T"))
    r = wx._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r.success and r.text_content.startswith("<html>")


@pytest.mark.unit
def test_weixin_try_playwright_crawler_import_error(monkeypatch):
    # Force ImportError path by patching sync_playwright import to raise
    def bad_import(*a, **k):
        raise ImportError("no playwright")
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', types.SimpleNamespace(sync_playwright=bad_import))
    r = wx._try_playwright_crawler("https://u", on_detail=None, shared_browser=None)
    assert r.success is False and "Playwright" in (r.error or "")


