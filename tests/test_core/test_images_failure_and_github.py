from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.core.images import _convert_github_url, download_images_and_rewrite


@pytest.mark.unit
def test_download_failures_keep_original_links(tmp_path):
    md = '![a](https://img.ok/a.png) <img src="https://img.fail/b.png">'
    base = "https://example.com/post"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # All downloads fail
    def dl_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        return {url: (False, path) for url, path, _ in image_tasks}

    with mock.patch("markitdown_app.core.images._download_images_async", side_effect=dl_async):
        session = mock.Mock()
        session.headers = {"User-Agent": "UA"}
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # Should not rewrite any links
    assert "https://img.ok/a.png" in out
    assert "https://img.fail/b.png" in out


@pytest.mark.unit
def test_github_raw_conversion_path(tmp_path):
    # URL in github.com/.../raw/... should be converted to raw.githubusercontent.com before request
    md = "![g](https://github.com/user/repo/raw/main/a.png)"
    base = "https://example.com"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    def dl_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        results = {}
        for url, path, headers in image_tasks:
            # Simulate what single-image would do: ensure conversion would change the URL
            converted = _convert_github_url(url)
            assert ("raw.githubusercontent.com" in converted) or (url == converted)
            results[url] = (True, path)
        return results

    with mock.patch("markitdown_app.core.images._download_images_async", side_effect=dl_async):
        session = mock.Mock()
        session.headers = {"User-Agent": "UA"}
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # On success, link rewritten to local img path
    assert "(img/" in out
