from __future__ import annotations

import asyncio
import os
from unittest import mock

import aiohttp
import pytest

from markurldown.core.images import _download_single_image


@pytest.mark.unit
def test_download_single_image_success_and_dedup(tmp_path, monkeypatch):
    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            class R:
                status = 200

                class C:
                    async def iter_chunked(self, n):
                        for c in (b"X" * 3, b"Y" * 3):
                            yield c

                content = C()

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *a):
                    return False

            return R()

    path1 = tmp_path / "a.img"
    path2 = tmp_path / "b.img"
    h2p = {}
    lock = asyncio.Lock()

    ok1, out1 = asyncio.run(
        _download_single_image(FakeSession(), "https://x/1", str(path1), None, h2p, lock)
    )
    # dedup: second download with same content should reuse first
    ok2, out2 = asyncio.run(
        _download_single_image(FakeSession(), "https://x/2", str(path2), None, h2p, lock)
    )
    assert ok1 and ok2 and out1 == out2


@pytest.mark.unit
def test_download_single_image_http_error(tmp_path, monkeypatch):
    class BadSession:
        async def get(self, *a, **k):
            class R:
                status = 500

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *a):
                    return False

            return R()

    ok, out = asyncio.run(
        _download_single_image(BadSession(), "https://x", str(tmp_path / "a.img"), None, None, None)
    )
    assert ok is False
