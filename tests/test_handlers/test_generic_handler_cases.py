from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.handlers import generic_handler


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    opt.handler_override = kwargs.get("handler_override")
    return opt


@pytest.mark.unit
def test_generic_convert_url_success(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(
        generic_handler,
        "_try_playwright_markitdown",
        lambda *a, **k: generic_handler.CrawlerResult(True, "T", "X" * 150),
    )
    monkeypatch.setattr(
        generic_handler,
        "normalize_markdown_headings",
        lambda text, title: f"{title}:{text[:3]}",
    )
    monkeypatch.setattr(generic_handler, "derive_md_filename", lambda title, url, ts: "file.md")

    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T"
    assert res.markdown.startswith("T:X")
    assert res.suggested_filename == "file.md"


@pytest.mark.unit
def test_generic_convert_url_retries_then_success(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/b", meta={})
    session = mock.Mock()

    calls = {"count": 0}

    def fake_try(*a, **k):
        calls["count"] += 1
        if calls["count"] == 1:
            return generic_handler.CrawlerResult(True, "T", "short")
        return generic_handler.CrawlerResult(True, "T", "Y" * 200)

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(generic_handler, "_try_playwright_markitdown", fake_try)
    monkeypatch.setattr(
        generic_handler,
        "normalize_markdown_headings",
        lambda text, title: text,
    )
    monkeypatch.setattr(generic_handler, "derive_md_filename", lambda title, url, ts: "retry.md")

    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T"
    assert res.markdown.startswith("Y")
    assert calls["count"] == 2


@pytest.mark.unit
def test_generic_convert_url_raises_after_retries(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/c", meta={})
    session = mock.Mock()

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(
        generic_handler,
        "_try_playwright_markitdown",
        lambda *a, **k: generic_handler.CrawlerResult(False, None, "", "err"),
    )

    with pytest.raises(Exception) as exc:
        generic_handler.convert_url(payload, session, make_opts())

    assert "Playwright策略获取失败" in str(exc.value)
