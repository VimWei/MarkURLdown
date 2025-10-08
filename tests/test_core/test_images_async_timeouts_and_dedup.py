from __future__ import annotations

import os
from datetime import datetime
from unittest import mock

import pytest

from markdownall.core.images import download_images_and_rewrite


@pytest.mark.unit
def test_async_timeout_errors_are_swallowed(tmp_path):
    md = "![a](https://img.t/a.png)"
    base = "https://example.com"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    def dl_async(image_tasks, aio_session, logger, hash_to_path, hash_lock):
        # Simulate timeout behavior by marking all downloads as failed, without raising
        return {url: (False, path) for url, path, _ in image_tasks}

    with mock.patch("markdownall.core.images._download_images_async", side_effect=dl_async):
        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # On failure, original link remains
    assert "https://img.t/a.png" in out


@pytest.mark.unit
def test_async_dedup_concurrency_same_path(tmp_path):
    md = "![a](https://cdn.example.com/a.png) ![b](https://cdn.example.com/b.png)"
    base = "https://example.com"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Simulate two URLs yielding identical content hashes
    def dl_async(image_tasks, aio_session, logger, hash_to_path, hash_lock):
        results = {}
        first_path = None
        for url, path, headers in image_tasks:
            # Write same bytes and deduplicate via shared map
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".part", "wb") as f:
                f.write(b"SAME-CONTENT")
            # mimic hasher result by keying on content
            if first_path is None:
                first_path = path
                # finalize first
                os.replace(path + ".part", path)
                results[url] = (True, path)
            else:
                # remove temp and point to first
                try:
                    os.remove(path + ".part")
                except Exception:
                    pass
                results[url] = (True, first_path)
        return results

    with (
        mock.patch("markdownall.core.images._download_images_async", side_effect=dl_async),
        mock.patch("markdownall.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = datetime(2025, 1, 1, 0, 0, 0)
        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    import re

    paths = re.findall(r"!\[[^\]]*\]\((img\/[^)]+)\)", out)
    assert len(paths) == 2 and paths[0] == paths[1]
