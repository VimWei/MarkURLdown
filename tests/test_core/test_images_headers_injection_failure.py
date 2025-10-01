from __future__ import annotations

from unittest import mock

import pytest

from markurldown.core.images import download_images_and_rewrite


@pytest.mark.unit
def test_special_headers_injection_failure_does_not_crash(tmp_path):
    # When headers are constructed for special domains, even if session.headers lacks keys or raises, it should not crash
    md = "![w](https://mmbiz.qpic.cn/a)"
    base = "https://mp.weixin.qq.com/s/xyz"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    def dl_async(image_tasks, aio_session, on_detail, hash_to_path, hash_lock):
        # assert headers constructed without KeyError
        for url, path, headers in image_tasks:
            assert "Referer" in headers
            assert "User-Agent" in headers
        return {url: (False, path) for url, path, _ in image_tasks}

    # session.headers might be missing; simulate minimal session
    session = mock.Mock()
    session.headers = {}

    with mock.patch("markurldown.core.images._download_images_async", side_effect=dl_async):
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # download failed, so original link remains
    assert "https://mmbiz.qpic.cn/a" in out
