from __future__ import annotations

import os
from datetime import datetime
from unittest import mock

import pytest

from markurldown.core.images import download_images_and_rewrite


@pytest.mark.unit
def test_image_dedup_by_content(tmp_path):
    md = "![a](https://cdn.example.com/a1.png) ![b](https://cdn.example.com/a2.png)"
    base = "https://example.com/post"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # two URLs, same content bytes -> should map to the same final file
    def fake_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        results = {}
        first_final = None
        for url, path, headers in image_tasks:
            # write same bytes for both
            with open(path, "wb") as f:
                f.write(b"SAME-CONTENT-BYTES")
            if first_final is None:
                first_final = path
                results[url] = (True, path)
            else:
                # simulate dedup: second maps to first file path
                results[url] = (True, first_final)
        return results

    with (
        mock.patch("markurldown.core.images._download_images_async", side_effect=fake_async),
        mock.patch("markurldown.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = datetime(2025, 1, 1, 0, 0, 0)
        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # Expect two links but both point to same file name
    import re

    paths = re.findall(r"!\[[^\]]*\]\((img\/[^)]+)\)", out)
    assert len(paths) == 2
    assert paths[0] == paths[1]


@pytest.mark.unit
def test_compact_resequence_rename(tmp_path):
    # Three images where second equals first (dedup), compact rename should produce _001, _002 only
    md = "![a](https://cdn.example.com/a.png) ![b](https://cdn.example.com/b.png) ![c](https://cdn.example.com/a.png)"
    base = "https://example.com/post"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # bytes: a.png -> AA, b.png -> BB, c same as a
    def fake_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        results = {}
        for url, path, headers in image_tasks:
            content = b"AA" if url.endswith("a.png") else b"BB"
            with open(path, "wb") as f:
                f.write(content)
            results[url] = (True, path)
        return results

    with (
        mock.patch("markurldown.core.images._download_images_async", side_effect=fake_async),
        mock.patch("markurldown.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = datetime(2025, 1, 1, 0, 0, 0)
        session = mock.Mock()
        out = download_images_and_rewrite(
            md, base, str(images_dir), session, enable_compact_rename=True
        )

    # After resequencing, only two unique files remain with sequential numbering 001, 002
    files = sorted(os.listdir(images_dir))
    # Expect two unique files with preserved .png extension
    assert files == ["20250101_000000_001.png", "20250101_000000_002.png"]
    # Markdown paths should use 001 for first unique, 002 for second unique; third references 001
    assert out.count("(img/20250101_000000_001.png)") == 2
    assert out.count("(img/20250101_000000_002.png)") == 1
