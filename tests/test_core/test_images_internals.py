from __future__ import annotations

from unittest import mock

import pytest

from markitdown_app.core.images import (
    ImageDomainConfig,
    _convert_github_url,
    _detect_image_format_from_header,
)


@pytest.mark.unit
def test_convert_github_url_rewrites_raw():
    u1 = "https://github.com/user/repo/raw/main/a.png"
    out = _convert_github_url(u1)
    assert out.startswith("https://raw.githubusercontent.com/user/repo/main/")

    u2 = "https://github.com/user/repo/blob/main/a.png"
    assert _convert_github_url(u2) == u2


@pytest.mark.unit
def test_detect_image_format_from_header_common_types():
    # Provide at least 8 bytes because detector returns empty for very short inputs
    assert _detect_image_format_from_header(b"\xff\xd8\xffaaaaaa") == ".jpg"
    assert _detect_image_format_from_header(b"\x89PNG\x0d\x0a\x1a\x0a") == ".png"
    assert _detect_image_format_from_header(b"GIF89a\x00\x00") == ".gif"
    assert _detect_image_format_from_header(b"RIFFxxxxWEBPxxxx") == ".webp"
    assert _detect_image_format_from_header(b"BMxxxxx\x00\x00") == ".bmp"
    assert _detect_image_format_from_header(b"II*\x00abcdabcd") == ".tiff"
    assert _detect_image_format_from_header(b"<svg>\x00\x00\x00") == ".svg"
    assert _detect_image_format_from_header(b"\x00\x00\x01\x00restxxxx") == ".ico"


@pytest.mark.unit
def test_image_domain_config_decisions():
    assert ImageDomainConfig.should_detect_format("pic1.zhimg.com") is True
    assert ImageDomainConfig.should_detect_format("zhimg.com") is True
    assert ImageDomainConfig.needs_special_headers("mmbiz.qpic.cn") is True
    assert ImageDomainConfig.is_reliable_cdn("cdn.example.com") is True
