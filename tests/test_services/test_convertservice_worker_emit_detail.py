from __future__ import annotations

import types
from unittest import mock

import pytest

from markitdown_app.app_types import ProgressEvent
from markitdown_app.services.convert_service import ConvertService


@pytest.mark.unit
def test_worker_emit_detail_uses_signal_and_fallback():
    svc = ConvertService()
    events = []

    # signals path
    class Sig:
        def __init__(self, bucket):
            self.progress_event = types.SimpleNamespace(emit=lambda ev: bucket.append(ev))

    svc._signals = Sig(events)

    # Use private helper via _emit_event_safe by calling through worker-embedded function signature
    ev = ProgressEvent(kind="detail", key="k")
    svc._emit_event_safe(ev, events.append)
    assert events and events[0].kind == "detail"

    # fallback path without signals
    svc._signals = None
    svc._emit_event_safe(ev, events.append)
    assert len(events) >= 2 and events[-1].kind == "detail"
