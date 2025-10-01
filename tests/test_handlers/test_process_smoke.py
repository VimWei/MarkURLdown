from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markurldown.core.handlers import appinn_handler as ap
from markurldown.core.handlers import nextjs_handler as nx
from markurldown.core.handlers import sspai_handler as sp
from markurldown.core.handlers import wordpress_handler as wp
from markurldown.core.handlers import zhihu_handler as zh


@pytest.mark.unit
def test_process_appinn_content_smoke():
    html = """
    <html><title>T - 小众软件</title><div class='entry-content'><p>Body</p></div></html>
    """
    r = ap._process_appinn_content(html, url="https://u", title_hint=None)
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_process_sspai_content_smoke():
    html = """
    <html><title>S - 少数派</title><article><div class='article-body'><div class='article__main__content wangEditor-txt'><p>Body</p></div></div></article></html>
    """
    r = sp._process_sspai_content(html, url="https://u", title_hint=None)
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_process_wordpress_content_smoke():
    html = """
    <html><title>W - Site</title><div id='content' role='main'><div class='entry-content'><p>Body</p></div></div></html>
    """
    r = wp._process_wordpress_content(html, url="https://u", title_hint=None)
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_process_nextjs_content_smoke():
    html = """
    <html><title>N - Site</title><main><div class='max-w-4xl mx-auto w-full px-6'><div><h1>T</h1></div><div class='content'><p>Body</p></div></div></main></html>
    """
    r = nx._process_nextjs_content(html, url="https://u", title_hint=None)
    assert r.title and "Body" in r.html_markdown


@pytest.mark.unit
def test_process_zhihu_content_smoke():
    html = """
    <html><title>Z</title><div class='Post-RichTextContainer'><p>Body</p></div></html>
    """
    r = zh._process_zhihu_content(html, title_hint="Z", url="https://zhuanlan.zhihu.com/p/1")
    assert r.title and "Body" in r.html_markdown
