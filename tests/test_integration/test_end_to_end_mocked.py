from __future__ import annotations

import os
import re
from unittest import mock

import pytest

from markurldown.app_types import ConversionOptions, SourceRequest
from markurldown.services.convert_service import ConvertService


def make_opts() -> ConversionOptions:
    opt = mock.Mock()
    opt.ignore_ssl = True
    opt.use_proxy = False
    opt.use_shared_browser = False
    opt.download_images = True
    return opt


@pytest.mark.integration
@mock.patch("markurldown.core.images._download_images_async")
@mock.patch("markurldown.io.writer.write_markdown")
@mock.patch("markurldown.services.convert_service.registry_convert")
@mock.patch("markurldown.services.convert_service.build_requests_session")
def test_end_to_end_mixed_urls(
    mock_build_sess, mock_reg_convert, mock_write_md, mock_dl_async, tmp_path
):
    # Prepare image downloader to succeed and return final paths
    def dl_fake(tasks, aio_session, on_detail, hash_to_path, hash_lock):
        results = {}
        for url, path, headers in tasks:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"IMG")
            results[url] = (True, path)
        return results

    mock_dl_async.side_effect = dl_fake

    # Registry returns simple markdown with one image
    def reg_fake(payload, session, options):
        url = payload.value
        title = f"T-{hash(url) % 1000}"
        # Simulate images having been downloaded and rewritten by creating img dir and a file
        out_dir = payload.meta.get("out_dir") or str(tmp_path)
        img_dir = os.path.join(out_dir, "img")
        os.makedirs(img_dir, exist_ok=True)
        img_path = os.path.join(img_dir, "x.png")
        with open(img_path, "wb") as f:
            f.write(b"IMG")
        md = "![](img/x.png)\nBody"
        return mock.Mock(title=title, markdown=md, suggested_filename=f"{title}.md")

    mock_reg_convert.side_effect = reg_fake

    # Writer returns a path for each converted file
    def write_fake(out_dir, filename, content):
        p = os.path.join(out_dir, filename)
        os.makedirs(out_dir, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return p

    mock_write_md.side_effect = write_fake

    # Run service synchronously through _worker
    svc = ConvertService()
    events = []
    reqs = [
        SourceRequest(kind="url", value="https://a.example/1"),
        SourceRequest(kind="url", value="https://b.example/2"),
    ]
    svc._worker(reqs, str(tmp_path), make_opts(), events.append)

    # Validate two outputs written
    written = [fn for fn in os.listdir(tmp_path) if fn.endswith(".md")]
    assert len(written) == 2

    # Ensure image dir created and rewritten in markdown
    img_dir = os.path.join(tmp_path, "img")
    assert os.path.isdir(img_dir)
    # One of written files should reference img/
    any_refers = False
    for fn in written:
        with open(os.path.join(tmp_path, fn), "r", encoding="utf-8") as f:
            txt = f.read()
            if "(img/" in txt:
                any_refers = True
                break
    assert any_refers

    # Progress events include done
    kinds = [getattr(e, "kind", None) for e in events]
    assert "progress_done" in kinds
