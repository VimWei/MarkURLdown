from __future__ import annotations

from unittest import mock

import pytest

from markurldown.app_types import ConversionOptions, ConvertPayload
from markurldown.core.handlers import generic_handler


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_generic_all_strategies_fail(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    CR = generic_handler.CrawlerResult
    monkeypatch.setattr(
        generic_handler, "_try_generic_with_filtering", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_lightweight_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_enhanced_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_direct_httpx", lambda *a, **k: CR(False, None, "", "e")
    )

    with pytest.raises(Exception):
        generic_handler.convert_url(payload, session, make_opts(filter_site_chrome=True))
