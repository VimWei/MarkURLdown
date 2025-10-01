from __future__ import annotations

from unittest import mock

import pytest

from markurldown.app_types import ConversionOptions, ConvertPayload
from markurldown.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_wordpress_success_basic():
    url = "https://skywind.me/blog/archives/100"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markurldown.core.registry.fetch_wordpress_article") as fw,
        mock.patch(
            "markurldown.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
        mock.patch("markurldown.core.registry.derive_md_filename", return_value="w.md"),
    ):
        fw.return_value = mock.Mock(title="W", html_markdown="ok content")
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "W"
    assert res.suggested_filename == "w.md"


@pytest.mark.unit
def test_wordpress_empty_fallback():
    url = "https://skywind.me/blog/archives/100"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markurldown.core.registry.fetch_wordpress_article") as fw,
        mock.patch("markurldown.core.registry.convert_url") as gen,
    ):
        fw.return_value = mock.Mock(title="any", html_markdown="   ")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"
