from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.core.images import download_images_and_rewrite


@pytest.mark.unit
def test_protocol_relative_and_data_urls(tmp_path):
    # Protocol-relative should inherit base scheme; data URLs should be ignored
    md = "![a](//cdn.example.com/a.png) ![b](data:image/png;base64,AAA)"
    base = "https://example.com/page"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    def dl_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        return {url: (True, path) for url, path, _ in image_tasks}

    with mock.patch("markitdown_app.core.images._download_images_async", side_effect=dl_async):
        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # data URL remains unchanged; protocol-relative rewritten to local path
    assert "data:image/png" in out
    assert "(img/" in out


@pytest.mark.unit
def test_html_img_single_quote_and_uppercase(tmp_path):
    md = "<IMG src='https://cdn.example.com/a.png' alt='x'>"
    base = "https://example.com"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    def dl_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        return {url: (True, path) for url, path, _ in image_tasks}

    with mock.patch("markitdown_app.core.images._download_images_async", side_effect=dl_async):
        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # Should rewrite uppercase IMG and single-quoted src
    assert "https://cdn.example.com/a.png" not in out
    assert "src='img/" in out


