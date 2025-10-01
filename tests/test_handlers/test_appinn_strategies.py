from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markurldown.core.handlers import appinn_handler as ap


@pytest.mark.unit
def test_appinn_try_httpx_crawler_success_and_error(monkeypatch):
    class Resp:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, timeout=30):
            return Resp("<html>ok</html>")

    httpx = types.SimpleNamespace(Client=Client)
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    session = types.SimpleNamespace(headers={"User-Agent": "UA"}, trust_env=True)
    r = ap._try_httpx_crawler(session, "https://u")
    assert r.success and r.html_markdown.startswith("<html>")

    class BadClient(Client):
        def get(self, *a, **k):
            raise RuntimeError("net")

    httpx_bad = types.SimpleNamespace(Client=BadClient)
    monkeypatch.setitem(sys.modules, "httpx", httpx_bad)
    r2 = ap._try_httpx_crawler(session, "https://u")
    assert r2.success is False


@pytest.mark.unit
def test_appinn_try_playwright_crawler_shared_and_error(monkeypatch):
    page = types.SimpleNamespace(goto=lambda *a, **k: None, wait_for_timeout=lambda ms: None)
    context = types.SimpleNamespace(new_page=lambda: page)
    monkeypatch.setattr(ap, "new_context_and_page", lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(ap, "read_page_content_and_title", lambda p: ("<html>OK</html>", "T"))
    monkeypatch.setattr(ap, "teardown_context_page", lambda c, p: None)
    r = ap._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r.success and r.html_markdown.startswith("<html>")

    monkeypatch.setattr(
        ap, "new_context_and_page", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r2 = ap._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r2.success is False
