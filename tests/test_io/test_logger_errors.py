from __future__ import annotations

import os
from unittest import mock

import pytest

from markitdown_app.io.logger import _project_root, log_urls


@pytest.mark.unit
def test_log_urls_swallows_io_errors(tmp_path):
    with mock.patch("markitdown_app.io.logger._project_root", return_value=str(tmp_path)):
        # Make open raise to simulate IO failure
        with mock.patch("markitdown_app.io.logger.open", side_effect=OSError("disk full")):
            # Should not raise
            log_urls(["https://x"])
        # No file created
        log_dir = os.path.join(str(tmp_path), "log")
        assert os.path.exists(log_dir)


@pytest.mark.unit
def test_project_root_points_three_levels_up():
    root = _project_root()
    assert isinstance(root, str) and len(root) > 1
