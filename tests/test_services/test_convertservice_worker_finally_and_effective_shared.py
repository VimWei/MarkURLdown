from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.app_types import SourceRequest
from markitdown_app.services.convert_service import ConvertService


def _make_options(shared: bool = True):
    opt = mock.Mock()
    opt.ignore_ssl = True
    opt.use_proxy = False
    opt.use_shared_browser = shared
    opt.download_images = False
    return opt


@pytest.mark.unit
@pytest.mark.service
def test_worker_finally_closes_browser_and_runtime_on_early_stop(tmp_path, monkeypatch):
    svc = ConvertService()
    events = []

    # One URL is enough. We'll stop before processing it, to exercise finally block.
    reqs = [SourceRequest(kind="url", value="https://example.com/a")]

    # Dummy runtime and browser that count closes
    counters = {"launch": 0, "close": 0, "stop": 0}

    class DummyBrowser:
        def close(self):
            counters["close"] += 1

    class DummyRuntime:
        def __init__(self):
            self.chromium = type("Chromium", (), {"launch": self.launch})()
        def launch(self, *a, **k):
            counters["launch"] += 1
            return DummyBrowser()
        def stop(self):
            counters["stop"] += 1

    # Patch playwright, session builder, URL decision
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: type("P", (), {"start": lambda self=None: DummyRuntime()})())
    monkeypatch.setattr("markitdown_app.services.convert_service.build_requests_session", lambda **k: object())
    monkeypatch.setattr("markitdown_app.core.registry.should_use_shared_browser_for_url", lambda url: True)

    # Trigger early stop right after entering loop
    def on_event(ev):
        events.append(ev)
        # Flip stop after we see status event to ensure loop exits quickly
        if getattr(ev, "kind", None) == "status":
            svc._should_stop = True

    # Run
    svc._worker(reqs, str(tmp_path), _make_options(shared=True), on_event)

    # Ensure runtime was launched then closed in finally
    assert counters["launch"] == 1
    assert counters["close"] >= 1
    assert counters["stop"] >= 1


@pytest.mark.unit
@pytest.mark.service
def test_effective_shared_browser_none_when_url_disallows_shared(tmp_path, monkeypatch):
    svc = ConvertService()
    events = []

    reqs = [SourceRequest(kind="url", value="https://no-shared.example/")]

    # Prepare runtime that will be closed immediately due to policy
    class DummyBrowser:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    class DummyRuntime:
        def __init__(self):
            self.browser = DummyBrowser()
            self.chromium = type("Chromium", (), {"launch": lambda *_a, **_k: self.browser})()
            self.stopped = False
        def stop(self):
            self.stopped = True

    runtime = DummyRuntime()

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: type("P", (), {"start": lambda self=None: runtime})())
    monkeypatch.setattr("markitdown_app.services.convert_service.build_requests_session", lambda **k: object())
    # Policy: never use shared for this URL
    monkeypatch.setattr("markitdown_app.core.registry.should_use_shared_browser_for_url", lambda url: False)

    captured_payloads = []

    def fake_convert(payload, session, options):
        captured_payloads.append(payload)
        return mock.Mock(title="T", markdown="# md", suggested_filename="f.md")

    monkeypatch.setattr("markitdown_app.services.convert_service.registry_convert", fake_convert)
    monkeypatch.setattr("markitdown_app.io.writer.write_markdown", lambda out_dir, fn, text: str(tmp_path / fn))

    svc._worker(reqs, str(tmp_path), _make_options(shared=True), events.append)

    # Payload must carry shared_browser=None due to policy
    assert captured_payloads and captured_payloads[0].meta.get("shared_browser") is None
    # And the initially created shared browser/runtime must be closed/stopped
    assert runtime.browser.closed is True
    assert runtime.stopped is True
    # No restart event should be present as there is no remaining URL needing shared browser
    keys = [getattr(e, "key", None) for e in events]
    assert "convert_shared_browser_restarted" not in keys


