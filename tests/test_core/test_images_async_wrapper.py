from __future__ import annotations

import asyncio
from unittest import mock

import pytest

from markurldown.core.images import _download_images_async


@pytest.mark.unit
def test_download_images_async_wraps_single_download_results():
    async def fake_single(session, url, path, headers, h2p, lock):
        return True, path

    async def run():
        return await _download_images_async(
            image_tasks=[("https://u", "/tmp/x", {})],
            session=None,
            on_detail=None,
            hash_to_path={},
            hash_lock=asyncio.Lock(),
        )

    with mock.patch("markurldown.core.images._download_single_image", side_effect=fake_single):
        out = asyncio.run(run())
    assert out["https://u"][0] is True
