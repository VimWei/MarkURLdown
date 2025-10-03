from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, SourceRequest
from markdownall.services.convert_service import ConvertService


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", True)
    opt.download_images = kwargs.get("download_images", False)
    return opt


class DummySignals:
    def __init__(self, bucket):
        class _E:
            def __init__(self, b):
                self._b = b

            def emit(self, ev):
                self._b.append(ev)

        self.progress_event = _E(bucket)


@pytest.mark.unit
@pytest.mark.service
def test_worker_shared_browser_start_failure_downgrades(tmp_path):
    svc = ConvertService()
    events = []
    reqs = [SourceRequest(kind="url", value="https://x.example/a")]

    with (
        mock.patch("markdownall.services.convert_service.build_requests_session"),
        mock.patch(
            "markdownall.core.registry.should_use_shared_browser_for_url", return_value=True
        ),
        mock.patch(
            "markdownall.services.convert_service.registry_convert",
            return_value=mock.Mock(title="T", markdown="# md", suggested_filename="f.md"),
        ),
        mock.patch("markdownall.io.writer.write_markdown", return_value=str(tmp_path / "out.md")),
        mock.patch("playwright.sync_api.sync_playwright", side_effect=RuntimeError("no pw")),
    ):
        # use_shared_browser=True but playwright startup fails -> should downgrade gracefully
        svc._worker(reqs, str(tmp_path), make_opts(use_shared_browser=True), events.append)

    kinds = [getattr(e, "kind", None) for e in events]
    assert "progress_init" in kinds
    assert ("progress_step" in kinds) or ("detail" in kinds)
    assert "progress_done" in kinds


@pytest.mark.unit
@pytest.mark.service
def test_worker_emits_via_signals_when_provided(tmp_path):
    svc = ConvertService()
    signal_events = []
    signals = DummySignals(signal_events)

    reqs = [SourceRequest(kind="url", value="https://x.example/a")]

    with (
        mock.patch("markdownall.services.convert_service.build_requests_session"),
        mock.patch(
            "markdownall.core.registry.should_use_shared_browser_for_url", return_value=True
        ),
        mock.patch(
            "markdownall.services.convert_service.registry_convert",
            return_value=mock.Mock(title="T", markdown="# md", suggested_filename="f.md"),
        ),
        mock.patch("markdownall.io.writer.write_markdown", return_value=str(tmp_path / "out.md")),
    ):
        # Run through public run() to set signals and avoid threading by calling _worker directly
        svc._signals = signals
        svc._worker(reqs, str(tmp_path), make_opts(use_shared_browser=False), lambda e: None)

    kinds = [getattr(e, "kind", None) for e in signal_events]
    assert "progress_init" in kinds and "progress_done" in kinds
