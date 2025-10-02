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
def test_appinn_success_basic():
    url = "https://www.appinn.com/abcd"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_appinn_article") as fa,
        mock.patch(
            "markdownall.core.normalize.normalize_markdown_headings", side_effect=lambda t, x: t
        ),
        mock.patch("markdownall.core.registry.derive_md_filename", return_value="a.md"),
    ):
        fa.return_value = mock.Mock(title="A", html_markdown="valid content" * 200)
        res = convert(payload, session, make_opts(download_images=False))

    assert res.title == "A"
    assert res.suggested_filename == "a.md"


@pytest.mark.unit
def test_appinn_too_short_fallback():
    url = "https://www.appinn.com/abcd"
    payload = ConvertPayload(kind="url", value=url, meta={})
    session = mock.Mock()

    with (
        mock.patch("markdownall.core.registry.fetch_appinn_article") as fa,
        mock.patch("markdownall.core.registry.convert_url") as gen,
    ):
        fa.return_value = mock.Mock(title="A", html_markdown="x" * 10)
        gen.return_value = mock.Mock(title="G", markdown="Generic", suggested_filename="g.md")
        res = convert(payload, session, make_opts())

    assert res.title == "G"
