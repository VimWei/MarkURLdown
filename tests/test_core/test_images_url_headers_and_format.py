from __future__ import annotations

import os
from datetime import datetime
from unittest import mock

import pytest

from markdownall.core.images import ImageDomainConfig, download_images_and_rewrite


@pytest.mark.unit
def test_images_adds_special_headers_for_weixin_and_sspai(tmp_path):
    md = '<img src="https://mmbiz.qpic.cn/abc"/> ![x](https://cdnfile.sspai.com/def)'
    base = "https://mp.weixin.qq.com/s/xyz"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Track headers passed into downloader by checking constructed image_tasks via side-effect
    captured_headers = {}

    def fake_async(image_tasks, aio_session, logger, hash_to_path, hash_lock):
        # image_tasks: list[(url, local_path, headers)]
        for url, path, headers in image_tasks:
            captured_headers[url] = headers or {}
        # Pretend success for both with .img extension to avoid format check branch interfering
        return {
            url: (True, path if path.endswith(".png") else path) for url, path, _ in image_tasks
        }

    with (
        mock.patch("markdownall.core.images._download_images_async", side_effect=fake_async),
        mock.patch("markdownall.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = datetime(2025, 1, 1, 0, 0, 0)

        session = mock.Mock()
        session.headers = {"User-Agent": "UA"}
        _ = download_images_and_rewrite(str(md), base, str(images_dir), session)

    # Both domains should request special headers
    weixin_url = "https://mmbiz.qpic.cn/abc"
    sspai_url = "https://cdnfile.sspai.com/def"
    assert "Referer" in captured_headers[weixin_url]
    assert "Referer" in captured_headers[sspai_url]
    assert captured_headers[weixin_url]["Referer"].startswith("https://mp.weixin.qq.com")


@pytest.mark.unit
def test_images_format_detection_and_rename(tmp_path):
    # zhimg.com triggers format detection; initial planned ext becomes .img then renamed to .png
    md = "![a](https://pic1.zhimg.com/xyz)"
    base = "https://zhuanlan.zhihu.com/p/1"
    images_dir = tmp_path / "img"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Expected final path after rename
    final_png = images_dir / "20250101_000000_001.png"

    def fake_async(image_tasks, aio_session, logger, hash_to_path, hash_lock):
        # Write a minimal PNG header to .img temp result to let detector decide .png
        results = {}
        for url, path, headers in image_tasks:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"\x89PNG\x0d\x0a\x1a\x0a")
            results[url] = (True, path)
        return results

    with (
        mock.patch("markdownall.core.images._download_images_async", side_effect=fake_async),
        mock.patch("markdownall.core.images._should_detect_image_format", return_value=True),
        mock.patch("markdownall.core.images.datetime") as dt_mock,
    ):
        dt_mock.now.return_value = datetime(2025, 1, 1, 0, 0, 0)

        session = mock.Mock()
        out = download_images_and_rewrite(md, base, str(images_dir), session)

    # File should be renamed to .png
    assert final_png.exists()
    assert "(img/20250101_000000_001.png)" in out
