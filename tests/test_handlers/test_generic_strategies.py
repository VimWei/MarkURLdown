from __future__ import annotations

import sys
import types
from unittest import mock

import pytest

from markurldown.core.handlers import generic_handler as gh


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
