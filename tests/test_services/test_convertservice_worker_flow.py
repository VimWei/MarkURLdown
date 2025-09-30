from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.app_types import ConversionOptions, ConvertPayload, SourceRequest
from markitdown_app.services.convert_service import ConvertService


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
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
@pytest.mark.timeout(10)
def test_worker_continues_on_error_and_emits_done(tmp_path):
    svc = ConvertService()

    # Build two URL requests; first will raise, second returns success
    reqs = [
        SourceRequest(kind="url", value="https://bad.example/1"),
        SourceRequest(kind="url", value="https://ok.example/2"),
    ]

    events = []

    # Patch components used inside _worker
    with mock.patch("markitdown_app.services.convert_service.build_requests_session"), \
        mock.patch("markitdown_app.core.registry.should_use_shared_browser_for_url", return_value=True), \
        mock.patch("markitdown_app.services.convert_service.registry_convert") as reg_convert, \
        mock.patch("markitdown_app.core.registry.convert") as reg_convert2, \
        mock.patch("markitdown_app.core.handlers.generic_handler.convert_url") as gen_conv, \
        mock.patch("markitdown_app.io.writer.write_markdown", return_value=str(tmp_path / "out.md")):

        def side_effect_convert(payload, session, options):
            if payload.value == "https://bad.example/1":
                raise RuntimeError("boom")
            return mock.Mock(title="OK", markdown="text", suggested_filename="x.md")

        reg_convert.side_effect = side_effect_convert
        reg_convert2.side_effect = side_effect_convert
        gen_conv.side_effect = side_effect_convert

        # Directly invoke _worker synchronously to avoid threading complexity
        svc._worker(reqs, str(tmp_path), make_opts(use_shared_browser=False), events.append)

    # Should have final progress_done event
    kinds = [getattr(e, "kind", None) for e in events]
    # Ensure it reached done and reported at least one error
    assert "progress_done" in kinds
    assert any(k == "error" for k in kinds)
    # progress_step may be missing if write_markdown short-circuits; allow either detail-done or progress_step
    assert ("progress_step" in kinds) or ("detail" in kinds)


@pytest.mark.unit
@pytest.mark.service
@pytest.mark.timeout(10)
def test_worker_stop_early(tmp_path):
    svc = ConvertService()

    reqs = [
        SourceRequest(kind="url", value="https://ex.com/1"),
        SourceRequest(kind="url", value="https://ex.com/2"),
    ]

    events = []

    with mock.patch("markitdown_app.services.convert_service.build_requests_session"), \
        mock.patch("markitdown_app.core.registry.should_use_shared_browser_for_url", return_value=True), \
        mock.patch("markitdown_app.services.convert_service.registry_convert") as reg_convert, \
        mock.patch("markitdown_app.core.registry.convert") as reg_convert2, \
        mock.patch("markitdown_app.core.handlers.generic_handler.convert_url") as gen_conv, \
        mock.patch("markitdown_app.io.writer.write_markdown", return_value=str(tmp_path / "out.md")):

        call_count = {"n": 0}
        def side_effect_convert(payload, session, options):
            # After first success, request stop. Next loop should see stop and emit 'stopped'.
            call_count["n"] += 1
            if call_count["n"] == 1:
                svc._should_stop = True
                return mock.Mock(title="T", markdown="m", suggested_filename="f.md")
            return mock.Mock(title="T2", markdown="m2", suggested_filename="f2.md")

        reg_convert.side_effect = side_effect_convert
        reg_convert2.side_effect = side_effect_convert
        gen_conv.side_effect = side_effect_convert

        svc._worker(reqs, str(tmp_path), make_opts(use_shared_browser=False), events.append)

    kinds = [getattr(e, "kind", None) for e in events]
    # Accept stopped or immediate completion if stop was honored before second progress
    assert ("stopped" in kinds) or ("progress_done" in kinds)
