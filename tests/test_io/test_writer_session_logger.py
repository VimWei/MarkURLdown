from __future__ import annotations

import io
import os
import re
from unittest import mock

import pytest

from markitdown_app.io.logger import log_urls
from markitdown_app.io.session import build_requests_session
from markitdown_app.io.writer import ensure_dir, write_markdown


@pytest.mark.unit
def test_writer_creates_dir_and_writes_file(tmp_path):
    out_dir = tmp_path / "out"
    path = write_markdown(str(out_dir), "a.md", "hello")
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == "hello"


@pytest.mark.unit
def test_build_requests_session_options(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy:8080")

    s1 = build_requests_session(ignore_ssl=True, use_proxy=True)
    assert s1.trust_env is True
    assert s1.verify is False
    assert "http" in s1.proxies and s1.proxies["http"].startswith("http://proxy")

    s2 = build_requests_session(ignore_ssl=False, use_proxy=False)
    assert s2.trust_env is False
    assert s2.verify is not False  # default True or CA bundle


@pytest.mark.unit
def test_log_urls_appends_daily_log(tmp_path):
    # Redirect project log dir to a temp dir via patching _project_root
    with mock.patch("markitdown_app.io.logger._project_root", return_value=str(tmp_path)):
        daily = os.path.join(str(tmp_path), "log")
        urls = ["https://a", "https://b"]
        log_urls(urls)
        # find today file
        files = os.listdir(daily)
        assert len(files) == 1
        p = os.path.join(daily, files[0])
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        # two lines with [HH:MM:SS] prefix
        lines = [l for l in content.strip().splitlines() if l]
        assert len(lines) == 2
        assert all(re.match(r"^\[\d{2}:\d{2}:\d{2}\] ", l) for l in lines)


@pytest.mark.unit
def test_log_urls_noop_on_empty(tmp_path):
    with mock.patch("markitdown_app.io.logger._project_root", return_value=str(tmp_path)):
        # Should not raise and not create files
        log_urls([])
        log_dir = os.path.join(str(tmp_path), "log")
        assert not os.path.exists(log_dir)
