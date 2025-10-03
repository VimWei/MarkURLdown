from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markdownall.core.handlers import generic_handler as gh


@pytest.mark.unit
def test_generic_try_lightweight_success_and_error(monkeypatch):
    md = types.SimpleNamespace(text_content="ok" * 60, metadata={"title": "T"})

    class FakeMID:
        def __init__(self):
            self._requests_session = types.SimpleNamespace(headers={})

        def convert(self, url):
            return md

    monkeypatch.setattr(gh, "MarkItDown", FakeMID)
    r = gh._try_lightweight_markitdown("https://u", session=types.SimpleNamespace(headers={}))
    assert r.success and r.text_content

    class BadMID(FakeMID):
        def convert(self, url):
            raise RuntimeError("x")

    monkeypatch.setattr(gh, "MarkItDown", BadMID)
    r2 = gh._try_lightweight_markitdown("https://u", session=types.SimpleNamespace(headers={}))
    assert r2.success is False


@pytest.mark.unit
def test_generic_try_enhanced_and_direct_httpx_error(monkeypatch):
    # Make playwright path raise
    def bad_import(*a, **k):
        raise RuntimeError("pw")

    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=bad_import)
    )
    r = gh._try_enhanced_markitdown("https://u", session=types.SimpleNamespace(headers={}))
    assert r.success is False

    # direct httpx path: patch MarkItDown and httpx client
    mid = types.SimpleNamespace(text_content="ok" * 60, metadata={"title": "T"})

    class FakeMID:
        def __init__(self):
            self._requests_session = types.SimpleNamespace(headers={})

        def convert(self, url):
            return mid

    monkeypatch.setattr(gh, "MarkItDown", FakeMID)

    class Client:
        def __init__(self, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, timeout=30):
            class R:
                def raise_for_status(self_inner):
                    return None

            return R()

    httpx = types.SimpleNamespace(Client=Client)
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    r2 = gh._try_direct_httpx(
        "https://u", session=types.SimpleNamespace(headers={}, trust_env=False)
    )
    assert r2.success and r2.text_content


@pytest.mark.unit
def test_generic_try_enhanced_success(monkeypatch):
    # Speed up sleeps inside enhanced path
    monkeypatch.setattr(gh.time, "sleep", lambda *a, **k: None)

    # Fake Playwright sync context
    class _Page:
        def __init__(self):
            self.headers = None

        def set_extra_http_headers(self, headers):
            self.headers = headers

        def goto(self, url, wait_until=None):
            self.url = url

        def content(self):
            return "<html><head><title>T</title></head><body>Hi</body></html>"

        def title(self):
            return "FromBrowser"

    class _Browser:
        def new_page(self):
            return _Page()

        def close(self):
            self.closed = True

    class _Chromium:
        def launch(self, headless=True):
            return _Browser()

    class _P:
        chromium = _Chromium()

    class _CM:
        def __enter__(self):
            return _P()

        def __exit__(self, exc_type, exc, tb):
            return False

    # Inject fake playwright
    import sys, types

    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=lambda: _CM())
    )

    # Fake MarkItDown converter returning non-empty content
    md_result = types.SimpleNamespace(text_content="OK", metadata={})

    class FakeMID:
        def __init__(self):
            self._requests_session = types.SimpleNamespace(headers={})

        def convert(self, html):
            return md_result

    monkeypatch.setattr(gh, "MarkItDown", FakeMID)

    r = gh._try_enhanced_markitdown("https://u", session=types.SimpleNamespace(headers={}))
    assert r.success is True
    assert r.title == "FromBrowser"
    assert r.text_content == "OK"


@pytest.mark.unit
def test_generic_try_enhanced_empty_result(monkeypatch):
    # Speed up sleeps
    monkeypatch.setattr(gh.time, "sleep", lambda *a, **k: None)

    # Reuse same fake playwright
    class _Page:
        def set_extra_http_headers(self, headers):
            pass

        def goto(self, url, wait_until=None):
            pass

        def content(self):
            return "<html></html>"

        def title(self):
            return "FromBrowser2"

    class _Browser:
        def new_page(self):
            return _Page()

        def close(self):
            pass

    class _Chromium:
        def launch(self, headless=True):
            return _Browser()

    class _P:
        chromium = _Chromium()

    class _CM:
        def __enter__(self):
            return _P()

        def __exit__(self, exc_type, exc, tb):
            return False

    import sys, types

    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", types.SimpleNamespace(sync_playwright=lambda: _CM())
    )

    # MarkItDown returns empty content
    md_result = types.SimpleNamespace(text_content="", metadata={})

    class FakeMID:
        def __init__(self):
            self._requests_session = types.SimpleNamespace(headers={})

        def convert(self, html):
            return md_result

    monkeypatch.setattr(gh, "MarkItDown", FakeMID)

    r = gh._try_enhanced_markitdown("https://u", session=types.SimpleNamespace(headers={}))
    assert r.success is False
    assert r.title == "FromBrowser2"
    assert r.text_content == ""