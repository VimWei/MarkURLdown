from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from markdownall.app_types import ProgressEvent
from markdownall.services.convert_service import LoggerAdapter


class DummySignals:
    def __init__(self):
        self.progress_event = Mock()


def test_logger_adapter_signal_emit():
    sig = DummySignals()
    ui = Mock()
    adapter = LoggerAdapter(ui, sig)

    adapter.info("hello")
    assert sig.progress_event.emit.called
    ev = sig.progress_event.emit.call_args[0][0]
    # structure check
    assert getattr(ev, "kind", None) == "status"
    assert getattr(ev, "text", None) == "hello"


def test_logger_adapter_signal_callable():
    # progress_event is callable, not a signal
    called = []

    class Sig:
        def __init__(self):
            # make progress_event a plain callable function
            self.progress_event = lambda ev: called.append(ev)

    sig = Sig()
    ui = Mock()
    adapter = LoggerAdapter(ui, sig)

    # Make progress_event itself callable
    adapter._emit_progress("detail", text="x")
    assert len(called) == 1


def test_logger_adapter_print_fallback_mainthread(capsys):
    # No signals, UI has no method; should print
    ui = object()
    adapter = LoggerAdapter(ui, None)
    adapter._call("status", "msg")
    out = capsys.readouterr().out
    assert "msg" in out


def test_logger_adapter_ui_method_mapping():
    ui = Mock()
    adapter = LoggerAdapter(ui, None)

    adapter._call("status", "s")
    ui.log_info.assert_called_with("s")

    adapter._call("detail", "d")
    ui.log_info.assert_called_with("d")

    adapter._call("progress_done", "ok")
    ui.log_success.assert_called_with("ok")

    adapter._call("error", "bad")
    ui.log_error.assert_called_with("bad")
