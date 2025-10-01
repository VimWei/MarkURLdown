from __future__ import annotations

import types

import pytest

from markurldown.core.handlers import appinn_handler as ap
from markurldown.core.handlers import nextjs_handler as nx
from markurldown.core.handlers import sspai_handler as sp
from markurldown.core.handlers import wordpress_handler as wp


@pytest.mark.unit
def test_fetch_appinn_article_smoke(monkeypatch):
    # Patch httpx strategy to return simple html
    monkeypatch.setattr(
        ap,
        "_try_httpx_crawler",
        lambda session, url: ap.FetchResult(
            title="T", html_markdown='<html><div class="entry-content">Body</div></html>'
        ),
    )
    r = ap.fetch_appinn_article(
        types.SimpleNamespace(headers={}, trust_env=True), "https://u", min_content_length=1
    )
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_fetch_sspai_article_smoke(monkeypatch):
    monkeypatch.setattr(
        sp,
        "_try_httpx_crawler",
        lambda session, url: sp.FetchResult(
            title="T",
            html_markdown='<html><article><div class="article-body"><div class="article__main__content wangEditor-txt">'
            + ("Body" * 100)
            + "</div></div></article></html>",
        ),
    )
    r = sp.fetch_sspai_article(types.SimpleNamespace(headers={}, trust_env=True), "https://u")
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_fetch_wordpress_article_smoke(monkeypatch):
    monkeypatch.setattr(
        wp,
        "_try_httpx_crawler",
        lambda session, url: wp.FetchResult(
            title="T",
            html_markdown='<html><div id="content" role="main"><div class="entry-content">'
            + ("Body" * 100)
            + "</div></div></html>",
        ),
    )
    r = wp.fetch_wordpress_article(types.SimpleNamespace(headers={}, trust_env=True), "https://u")
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_fetch_nextjs_article_smoke(monkeypatch):
    monkeypatch.setattr(
        nx,
        "_try_httpx_crawler",
        lambda session, url: nx.FetchResult(
            title="T",
            html_markdown='<html><main><div class="max-w-4xl mx-auto w-full px-6"><div><h1>T</h1></div><div class="content">'
            + ("Body" * 100)
            + "</div></div></main></html>",
        ),
    )
    r = nx.fetch_nextjs_article(types.SimpleNamespace(headers={}, trust_env=True), "https://u")
    assert r.title and "Body" in r.html_markdown
