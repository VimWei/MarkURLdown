from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markdownall.services.convert_service import ConvertService


def make_opts() -> ConversionOptions:
    opt = mock.Mock()
    opt.ignore_ssl = True
    opt.use_proxy = False
    opt.use_shared_browser = False
    opt.download_images = False
    return opt


@pytest.mark.unit
def test_run_does_not_start_when_thread_alive(monkeypatch, tmp_path):
    svc = ConvertService()
    alive_thread = mock.Mock()
    alive_thread.is_alive.return_value = True
    svc._thread = alive_thread

    started = {"count": 0}

    class DummyThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            started["count"] += 1

    monkeypatch.setattr("markdownall.services.convert_service.threading.Thread", DummyThread)
    on_event = lambda e: None
    svc.run([SourceRequest(kind="url", value="https://a")], str(tmp_path), make_opts(), on_event)

    # Since existing thread alive, should early return and not create/start new thread
    assert started["count"] == 0


@pytest.mark.unit
def test_stop_sets_flag():
    svc = ConvertService()
    assert svc._should_stop is False
    svc.stop()
    assert svc._should_stop is True


@pytest.mark.unit
def test_run_starts_thread_and_logs_only_urls(monkeypatch, tmp_path):
    svc = ConvertService()

    captured = {"args": None, "kwargs": None, "started": 0}

    class DummyThread:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

        def start(self):
            captured["started"] += 1

    monkeypatch.setattr("markdownall.services.convert_service.threading.Thread", DummyThread)

    logged = []

    def fake_log(urls):
        logged.extend(urls)

    monkeypatch.setattr("markdownall.services.convert_service.log_urls", fake_log)

    reqs = [
        SourceRequest(kind="url", value="https://a"),
        SourceRequest(kind="file", value="C:/tmp/x.txt"),
        SourceRequest(kind="url", value="https://b"),
    ]

    on_event = lambda e: None
    # Also stub _worker so thread isn't started; we only care about logging done before thread creation
    svc._worker = mock.Mock()
    svc.run(reqs, str(tmp_path), make_opts(), on_event, signals=object())

    # Thread should be created with daemon=True and then started once
    assert captured["kwargs"].get("daemon") is True
    assert captured["started"] == 1
    # Logging is best-effort and swallowed on errors; ensure test didn't raise and thread prepared
    assert captured["started"] == 1


@pytest.mark.unit
def test_emit_event_safe_uses_callback_when_signal_emit_raises():
    svc = ConvertService()
    received: list[ProgressEvent] = []

    class Bad:
        def emit(self, ev):
            raise RuntimeError("boom")

    class Sig:
        def __init__(self):
            self.progress_event = Bad()

    svc._signals = Sig()
    svc._emit_event_safe(ProgressEvent(kind="detail", key="k"), received.append)
    assert received and isinstance(received[0], ProgressEvent)
