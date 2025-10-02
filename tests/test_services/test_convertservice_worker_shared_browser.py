from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import SourceRequest
from markdownall.services.convert_service import ConvertService


def _make_options():
    opt = mock.Mock()
    opt.ignore_ssl = True
    opt.use_proxy = False
    opt.use_shared_browser = True
    opt.download_images = False
    return opt


@pytest.mark.unit
@pytest.mark.service
def test_shared_browser_start_close_and_restart(tmp_path):
    svc = ConvertService()
    events = []

    # URL A: handler does NOT use shared browser -> should close if running
    # URL B: handler DOES use shared browser -> should restart shared browser before processing
    reqs = [
        SourceRequest(kind="url", value="https://no-shared.example/a"),
        SourceRequest(kind="url", value="https://needs-shared.example/b"),
    ]

    # Track created/closed status
    class DummyBrowser:
        def __init__(self, label):
            self.label = label
            self.closed = False

        def close(self):
            self.closed = True

    dummy_runtime = mock.MagicMock()
    dummy_runtime.chromium.launch.return_value = DummyBrowser("initial")

    with (
        mock.patch("markdownall.services.convert_service.build_requests_session"),
        mock.patch(
            "markdownall.services.convert_service.registry_convert",
            return_value=mock.Mock(title="T", markdown="# m", suggested_filename="f.md"),
        ),
        mock.patch("markdownall.io.writer.write_markdown", return_value=str(tmp_path / "out.md")),
        mock.patch("markdownall.core.registry.get_handler_for_url") as get_handler_for_url,
        mock.patch("markdownall.core.registry.should_use_shared_browser_for_url") as should_use,
        mock.patch("markdownall.services.convert_service.threading.Thread") as ThreadMock,
        mock.patch("playwright.sync_api.sync_playwright") as sp,
    ):

        # Simulate thread-less execution by directly calling _worker; we patch Thread just to avoid accidental spawn
        ThreadMock.return_value = mock.Mock()

        # Configure should_use_shared_browser_for_url decisions
        def _should_use(url):
            return url.endswith("/b")  # only second URL should use shared

        should_use.side_effect = _should_use

        # Provide handler name for logging clarity (not strictly required for assertions)
        handler_mock = mock.Mock()
        handler_mock.handler_name = "HandlerX"
        get_handler_for_url.return_value = handler_mock

        # First start() call returns a runtime; later restart also returns a new runtime
        sp.return_value.start.side_effect = [dummy_runtime, dummy_runtime]

        # Run
        svc._worker(reqs, str(tmp_path), _make_options(), events.append)

    # Collect emitted event keys for browser lifecycle
    keys = [getattr(e, "key", None) for e in events]
    # Initial shared browser started
    assert "convert_shared_browser_started" in keys
    # After first URL (not using shared), it should be closed and later restarted before second URL
    assert "convert_shared_browser_restarted" in keys
