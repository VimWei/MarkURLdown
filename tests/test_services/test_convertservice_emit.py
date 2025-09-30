from __future__ import annotations

from dataclasses import dataclass

import pytest

from markitdown_app.app_types import ProgressEvent
from markitdown_app.services.convert_service import ConvertService


@dataclass
class DummySignal:
    captured: list

    def emit(self, event: ProgressEvent) -> None:
        self.captured.append(event)


class DummySignals:
    def __init__(self, bucket: list):
        self.progress_event = DummySignal(bucket)


@pytest.mark.unit
def test_emit_event_safe_with_signals():
    svc = ConvertService()
    bucket: list[ProgressEvent] = []
    svc._signals = DummySignals(bucket)

    received: list[ProgressEvent] = []

    def cb(ev: ProgressEvent):
        received.append(ev)

    ev = ProgressEvent(kind="detail", key="k")
    svc._emit_event_safe(ev, cb)

    # When signals exist, it should use signals (bucket captures). Callback is a fallback.
    assert bucket and bucket[0].kind == "detail"


@pytest.mark.unit
def test_emit_event_safe_without_signals_uses_callback():
    svc = ConvertService()
    svc._signals = None
    received: list[ProgressEvent] = []

    def cb(ev: ProgressEvent):
        received.append(ev)

    ev = ProgressEvent(kind="status", key="k2")
    svc._emit_event_safe(ev, cb)
    assert received and received[0].kind == "status"
