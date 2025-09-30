from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.core.images import download_images_and_rewrite


@pytest.mark.unit
def test_download_images_and_rewrite_maps_only_success(tmp_path):
    md = "![a](https://img.ok/a.png) ![b](https://img.fail/b.png)"
    base = "https://example.com/post"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Simulate downloader results: first succeeds, second fails
    fake_results = {
        "https://img.ok/a.png": (True, str(images_dir / "20250101_000000_001.png")),
        "https://img.fail/b.png": (False, str(images_dir / "20250101_000000_002.png")),
    }

    # Patch only the async downloader; let asyncio.run execute immediately with our patched coroutine
    with (
        mock.patch("markitdown_app.core.images._download_images_async", return_value=fake_results),
        mock.patch("markitdown_app.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = dt_mock.strptime("2025-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        dt_mock.strftime = lambda dt, fmt: "20250101_000000"

        session = mock.Mock()
        rewritten = download_images_and_rewrite(
            md, base, str(images_dir), session, should_stop=lambda: False
        )

    # The success image should be rewritten to local path; failure stays original
    assert "(img/" in rewritten
    assert "https://img.fail/b.png" in rewritten
