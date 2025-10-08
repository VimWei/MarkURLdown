from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import SourceRequest
from markdownall.services.convert_service import ConvertService


def _make_options():
    opt = mock.Mock()
    opt.ignore_ssl = True
    opt.use_proxy = False
    opt.use_shared_browser = False
    opt.download_images = False
    return opt


@pytest.mark.unit
@pytest.mark.service
def test_worker_emit_detail_handles_str_and_dict(tmp_path, monkeypatch):
    svc = ConvertService()
    events = []

    reqs = [SourceRequest(kind="url", value="https://example.com/item")]

    # Patch via monkeypatch to be robust under combined runs
    monkeypatch.setattr(
        "markdownall.services.convert_service.build_requests_session", lambda **k: object()
    )
    monkeypatch.setattr(
        "markdownall.core.registry.should_use_shared_browser_for_url", lambda url: True
    )
    monkeypatch.setattr(
        "markdownall.io.writer.write_markdown",
        lambda out_dir, fn, text: str(tmp_path / "out.md"),
    )

    def _reg_convert_side_effect(payload, session, options):
        # on_detail callback is no longer used
        return mock.Mock(title="T", markdown="# md", suggested_filename="f.md")

    # Critically, patch the alias used inside convert_service module
    monkeypatch.setattr(
        "markdownall.services.convert_service.registry_convert", _reg_convert_side_effect
    )
    # Also patch potential fallbacks to ensure no unexpected network/logic paths
    monkeypatch.setattr("markdownall.core.registry.convert", _reg_convert_side_effect)
    monkeypatch.setattr(
        "markdownall.core.handlers.generic_handler.convert_url",
        lambda payload, session, options: _reg_convert_side_effect(payload, session, options),
    )
    # Patch the re-export used inside core.registry as well
    monkeypatch.setattr(
        "markdownall.core.registry.convert_url",
        lambda payload, session, options: _reg_convert_side_effect(payload, session, options),
    )

    # Run synchronously
    svc._worker(reqs, str(tmp_path), _make_options(), events.append, None)

    # Collect emitted detail events (text-form and key/data-form)
    detail_events = [e for e in events if getattr(e, "kind", None) == "detail"]
    assert detail_events, "expected at least detail events"

    # There should be at least one plain-text detail
    assert any(getattr(e, "text", None) == "simple text message" for e in detail_events)

    # And at least one structured detail with key/data propagated
    assert any(
        getattr(e, "key", None) == "stage" and getattr(e, "data", None) == {"step": 1}
        for e in detail_events
    )
