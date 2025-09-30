from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markitdown_app.core.handlers import sspai_handler as sp


@pytest.mark.unit
def test_try_httpx_crawler_success_and_error(monkeypatch):
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
    r = sp._try_httpx_crawler(session, "https://u")
    assert r.success and r.html_markdown.startswith("<html>")

    # error path
    class BadClient(Client):
        def get(self, *a, **k):
            raise RuntimeError("net")

    httpx_bad = types.SimpleNamespace(Client=BadClient)
    monkeypatch.setitem(sys.modules, "httpx", httpx_bad)
    r2 = sp._try_httpx_crawler(session, "https://u")
    assert r2.success is False


@pytest.mark.unit
def test_try_playwright_crawler_shared_and_error(monkeypatch):
    # shared browser path
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
    )
    context = types.SimpleNamespace(new_page=lambda: page)
    # patch helpers used inside
    monkeypatch.setattr(sp, "new_context_and_page", lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(sp, "read_page_content_and_title", lambda p: ("<html>OK</html>", "T"))
    monkeypatch.setattr(sp, "teardown_context_page", lambda c, p: None)

    r = sp._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r.success and r.html_markdown.startswith("<html>")

    # error path: raise inside to hit except
    monkeypatch.setattr(
        sp, "new_context_and_page", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r2 = sp._try_playwright_crawler("https://u", on_detail=None, shared_browser=object())
    assert r2.success is False
