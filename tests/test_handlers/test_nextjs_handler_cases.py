from __future__ import annotations

from unittest import mock

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.registry import convert


def make_opts(**kwargs) -> ConversionOptions:
    opt = mock.Mock()
    opt.download_images = kwargs.get("download_images", False)
    opt.ignore_ssl = kwargs.get("ignore_ssl", True)
    opt.use_proxy = kwargs.get("use_proxy", False)
    opt.use_shared_browser = kwargs.get("use_shared_browser", False)
    return opt


@pytest.mark.unit
def test_nextjs_success_basic():
    url = "https://guangzhengli.com/blog/hello"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_nextjs_article") as fn,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
        mock.patch("markdownall.core.registry.derive_md_filename", return_value="n.md"),
    ):
        fn.return_value = mock.Mock(title="N", html_markdown="ok content")
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "N"
    assert res.suggested_filename == "n.md"


@pytest.mark.unit
def test_nextjs_empty_fallback():
    url = "https://guangzhengli.com/blog/hello"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_nextjs_article") as fn,
        mock.patch("markdownall.core.registry.convert_url") as gen,
    ):
        fn.return_value = mock.Mock(title="any", html_markdown="   ")
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"
