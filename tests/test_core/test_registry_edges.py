from __future__ import annotations

import pytest

from markdownall.core.registry import (
    get_handler_for_url,
    should_use_shared_browser_for_url,
)


@pytest.mark.unit
def test_get_handler_for_url_unknown():
    assert get_handler_for_url("https://unknown.example.com/page") is None


@pytest.mark.unit
def test_should_use_shared_browser_default_true_for_unknown():
    assert should_use_shared_browser_for_url("https://unknown.example.com/page") is True
