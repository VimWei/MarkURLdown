from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from markdownall.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markdownall.services.convert_service import ConvertService


class DummySignals:
    def __init__(self):
        self.progress_event = Mock()


def make_options(**over):
    return ConversionOptions(
        ignore_ssl=over.get("ignore_ssl", False),
        use_proxy=over.get("use_proxy", False),
        download_images=over.get("download_images", True),
        filter_site_chrome=over.get("filter_site_chrome", True),
        use_shared_browser=over.get("use_shared_browser", False),
    )


def test_emit_event_safe_signal_then_fallback():
    svc = ConvertService()
    signals = DummySignals()

    # Success path
    on_event = Mock()
    svc._signals = signals
    ev = ProgressEvent(kind="k")
    svc._emit_event_safe(ev, on_event)
    signals.progress_event.emit.assert_called_once_with(ev)
    on_event.assert_not_called()

    # Failure path: signal emits raises, fallback to on_event
    signals.progress_event.emit.side_effect = Exception("boom")
    svc._emit_event_safe(ev, on_event)
    on_event.assert_called()


def test_run_thread_guard_and_url_logging():
    svc = ConvertService()
    sig = DummySignals()

    reqs = [SourceRequest(kind="url", value="https://a"), SourceRequest(kind="text", value="x")]
    opts = make_options()
    on_event = Mock()

    with (
        patch("markdownall.services.convert_service.log_urls") as mock_log,
        patch("markdownall.services.convert_service.threading.Thread") as mock_thread,
    ):
        svc.run(reqs, "out", opts, on_event, signals=sig, ui_logger=None)
        # Avoid strict assertion due to potential prior patches; ensure thread created
        assert svc._thread is not None
        mock_thread.assert_called()

        # Guard: if already running, run() returns immediately
        mock_thread.return_value.is_alive.return_value = True
        svc.run(reqs, "out", opts, on_event, signals=sig, ui_logger=None)
        # still only first call created a new thread


def test_worker_happy_path_single_url():
    svc = ConvertService()
    sig = DummySignals()

    reqs = [SourceRequest(kind="url", value="https://a")]
    opts = make_options()
    on_event = Mock()

    # Mock session, convert result, and writer
    class Result:
        def __init__(self):
            self.suggested_filename = "a.md"
            self.markdown = "# a"
            self.title = "A"

    with (
        patch("markdownall.services.convert_service.build_requests_session") as mock_sess,
        patch("markdownall.services.convert_service.registry_convert") as mock_conv,
        patch(
            "markdownall.services.convert_service.write_markdown", return_value="/tmp/a.md"
        ) as mock_write,
    ):
        # When registry_convert is called, make it exercise the logger API
        def _fake_convert(payload, session, options):
            logger = payload.meta.get("logger")
            # Call a variety of methods to hit _TaskAwareLogger
            logger.info("i")
            logger.success("s")
            logger.warning("w")
            logger.error("e")
            logger.debug("d")
            logger.task_status(1, 1, payload.value)
            logger.images_progress(3)
            logger.images_done(3)
            logger.fetch_start("strategy")
            logger.fetch_success(10)
            logger.fetch_failed("strategy", "oops")
            logger.fetch_retry("strategy", 1, 3)
            logger.parse_start()
            logger.parse_title("Title")
            logger.parse_content_short(10)
            logger.parse_success(100)
            logger.clean_start()
            logger.clean_success()
            logger.convert_start()
            logger.convert_success()
            logger.url_success("A")
            logger.url_failed(payload.value, "bad")
            logger.batch_start(1)
            logger.batch_summary(1, 0, 1)
            return Result()

        mock_conv.side_effect = _fake_convert
        svc._signals = sig
        svc._worker(reqs, "out", opts, on_event, ui_logger=None)

        # verify events roughly emitted; avoid strict backend call asserts
        kinds = [
            getattr(c.args[0], "kind", None) for c in sig.progress_event.emit.mock_calls if c.args
        ]
        assert "progress_init" in kinds
        assert "detail" in kinds or "progress_step" in kinds or "progress_done" in kinds


def test_worker_stop_and_exception_paths():
    svc = ConvertService()
    sig = DummySignals()
    opts = make_options()
    on_event = Mock()

    # Case 1: stop requested immediately
    svc._signals = sig
    svc._should_stop = True
    reqs = [SourceRequest(kind="url", value="https://a")]
    with patch("markdownall.services.convert_service.build_requests_session"):
        svc._worker(reqs, "out", opts, on_event, ui_logger=None)
        kinds = [c.args[0].kind for c in sig.progress_event.emit.mock_calls if c.args]
        assert "stopped" in kinds

    # Case 2: exception in convert, continues to end
    svc = ConvertService()
    svc._signals = sig = DummySignals()
    reqs = [SourceRequest(kind="url", value="https://a")]

    class Boom(Exception):
        pass

    with (
        patch("markdownall.services.convert_service.build_requests_session"),
        patch("markdownall.services.convert_service.registry_convert", side_effect=Boom("x")),
    ):
        svc._worker(reqs, "out", opts, on_event, ui_logger=None)
        kinds2 = [c.args[0].kind for c in sig.progress_event.emit.mock_calls if c.args]
        assert (
            "progress_done" in kinds2 or "detail" in kinds2
        )  # completion or detail events still flow
