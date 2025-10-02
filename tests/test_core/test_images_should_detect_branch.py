from __future__ import annotations

import pytest

from markdownall.core.images import _should_detect_image_format


@pytest.mark.unit
def test_should_detect_for_known_domains():
    assert _should_detect_image_format("https://pic1.zhimg.com/abc") is True
    assert _should_detect_image_format("https://mmbiz.qpic.cn/abc") is True


@pytest.mark.unit
def test_should_not_detect_for_reliable_cdn_without_ext():
    # reliable CDN host but no extension -> returns False
    assert _should_detect_image_format("https://cdn.example.com/image/noext") is False


@pytest.mark.unit
def test_should_not_detect_for_unknown_noext():
    # unknown domain and no extension -> conservative False
    assert _should_detect_image_format("https://files.example.com/noext") is False


@pytest.mark.unit
def test_should_not_detect_when_has_extension():
    assert _should_detect_image_format("https://any.example.com/a.png") is False
