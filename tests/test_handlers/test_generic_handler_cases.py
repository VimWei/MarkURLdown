from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.app_types import ConversionOptions, ConvertPayload
from markitdown_app.core.handlers import generic_handler


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_generic_convert_url_success_first_strategy(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    # Speed up
    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    CR = generic_handler.CrawlerResult
    # Patch internal strategies to succeed on first
    monkeypatch.setattr(
        generic_handler, "_try_lightweight_markitdown", lambda *a, **k: CR(True, "T", "X" * 120)
    )
    monkeypatch.setattr(
        generic_handler, "_try_enhanced_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_direct_httpx", lambda *a, **k: CR(False, None, "", "e")
    )

    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T"
    assert res.markdown.strip().startswith("X")


@pytest.mark.unit
def test_generic_convert_url_fallback_to_httpx(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    # Speed up
    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    CR = generic_handler.CrawlerResult
    # First two fail, third succeeds
    monkeypatch.setattr(
        generic_handler, "_try_lightweight_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_enhanced_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_direct_httpx", lambda *a, **k: CR(True, "T3", "Y" * 150)
    )

    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T3"
    assert len(res.markdown) > 0
