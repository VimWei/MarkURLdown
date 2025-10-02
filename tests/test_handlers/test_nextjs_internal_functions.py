from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markdownall.core.handlers import nextjs_handler as nx


@pytest.mark.unit
def test_extract_nextjs_title_and_meta():
    soup = BeautifulSoup("<main><div class='max-w-4xl'><div><h1>T</h1></div></div></main>", "lxml")
    assert nx._extract_nextjs_title(soup) == "T"
    soup2 = BeautifulSoup("<title>X - Site</title>", "lxml")
    assert nx._extract_nextjs_title(soup2) == "X"


@pytest.mark.unit
def test_extract_nextjs_metadata():
    html = """
    <div class='author'><a>AuthorN</a></div>
    <time class='text-sm' datetime='2025-02-02'>ignored</time>
    <div class='categories'><a>CatN</a></div>
    <div class='tags'><a>tagN</a></div>
    """
    soup = BeautifulSoup(html, "lxml")
    meta = nx._extract_nextjs_metadata(soup)
    assert meta["author"] == "AuthorN"
    assert meta["publish_time"] == "2025-02-02"
    assert meta["categories"] == "CatN"
    assert meta["tags"] == "tagN"


@pytest.mark.unit
def test_build_nextjs_header_parts_and_content_element_and_clean():
    html = """
    <html><body>
      <main>
        <div class='max-w-4xl mx-auto w-full px-6'><div><h1>TitleN</h1></div><p class='text-sm'>time</p><div class='content'><p>Body</p></div></div>
      </main>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    title, parts = nx._build_nextjs_header_parts(soup, url="https://u")
    assert title == "TitleN"
    head = "\n".join(parts)
    assert "# TitleN" in head and "来源：https://u" in head
    content = nx._build_nextjs_content_element(soup)
    assert content and "Body" in content.get_text()
