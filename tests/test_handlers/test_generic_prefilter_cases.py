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
    opt.filter_site_chrome = True
    return opt


@pytest.mark.unit
def test_generic_prefilter_success(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    CR = generic_handler.CrawlerResult

    # prefilter succeeds, others won't be called meaningfully
    monkeypatch.setattr(
        generic_handler, "_try_generic_with_filtering", lambda *a, **k: CR(True, "T", "X" * 200)
    )
    monkeypatch.setattr(
        generic_handler, "_try_lightweight_markitdown", lambda *a, **k: CR(False, None, "", "e")
    )
    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T"


@pytest.mark.unit
def test_generic_prefilter_fallback_to_next(monkeypatch):
    payload = ConvertPayload(kind="url", value="https://x.example/a", meta={})
    session = mock.Mock()

    monkeypatch.setattr(generic_handler.time, "sleep", lambda *a, **k: None)
    CR = generic_handler.CrawlerResult

    # prefilter fails then lightweight succeeds
    monkeypatch.setattr(
        generic_handler, "_try_generic_with_filtering", lambda *a, **k: CR(False, None, "", "e")
    )
    monkeypatch.setattr(
        generic_handler, "_try_lightweight_markitdown", lambda *a, **k: CR(True, "T2", "Y" * 200)
    )
    res = generic_handler.convert_url(payload, session, make_opts())
    assert res.title == "T2"


@pytest.mark.unit
def test_try_generic_with_filtering_success_bytes_fallback(monkeypatch):
    session = mock.Mock()
    session.headers = {"User-Agent": "UA"}
    raw_html = "<html><head><title>T</title></head><body><h1>T</h1><p>body</p></body></html>"

    class DummyResp:
        text = raw_html

        def raise_for_status(self):
            return None

    session.get.return_value = DummyResp()

    class DummyMD:
        def __init__(self):
            self._requests_session = type("S", (), {"headers": {}})()

        def convert(self, content):
            # First attempt (string) fails, bytes succeeds
            if isinstance(content, bytes):
                return type("R", (), {"text_content": "MD", "metadata": {"title": "T"}})()
            raise RuntimeError("string path failed")

    monkeypatch.setattr("markurldown.core.handlers.generic_handler.MarkItDown", lambda: DummyMD())
    monkeypatch.setattr(
        "markurldown.core.handlers.generic_handler.apply_dom_filters",
        lambda html, sels: (raw_html, ["x"]),
    )

    r = generic_handler._try_generic_with_filtering("https://example.com/x", session)
    assert r.success and r.title == "T" and r.text_content == "MD"


@pytest.mark.unit
def test_try_generic_with_filtering_tempfile_fallback(monkeypatch, tmp_path):
    session = mock.Mock()
    session.headers = {"User-Agent": "UA"}
    raw_html = "<html><head><title>T2</title></head><body><h1>T2</h1><p>body</p></body></html>"

    class DummyResp:
        text = raw_html

        def raise_for_status(self):
            return None

    session.get.return_value = DummyResp()

    class DummyMD:
        def __init__(self):
            self._requests_session = type("S", (), {"headers": {}})()

        def convert(self, content):
            raise RuntimeError("fail both string and bytes")

    monkeypatch.setattr("markurldown.core.handlers.generic_handler.MarkItDown", lambda: DummyMD())
    monkeypatch.setattr(
        "markurldown.core.handlers.generic_handler.apply_dom_filters",
        lambda html, sels: (raw_html, ["x"]),
    )

    with mock.patch("tempfile.NamedTemporaryFile") as ntf:
        # Create a fake named temp file returning a name
        class T:
            def __init__(self):
                self.name = str(tmp_path / "t.html")

            def write(self, b):
                (tmp_path / "t.html").write_bytes(b)

            def close(self):
                return None

        ntf.return_value = T()

        # Make convert() succeed when MD receives a temp file path
        def convert_path(path):
            if isinstance(path, str) and path.endswith(".html"):
                return type("R", (), {"text_content": "MD2", "metadata": {"title": "T2"}})()
            raise RuntimeError("unexpected input")

        # Swap in a new DummyMD with path-based convert
        class DummyMD2:
            def __init__(self):
                self._requests_session = type("S", (), {"headers": {}})()

            def convert(self, content):
                return convert_path(content)

        monkeypatch.setattr(
            "markurldown.core.handlers.generic_handler.MarkItDown", lambda: DummyMD2()
        )

        r = generic_handler._try_generic_with_filtering("https://example.com/y", session)
    assert r.success and r.title == "T2" and r.text_content == "MD2"
