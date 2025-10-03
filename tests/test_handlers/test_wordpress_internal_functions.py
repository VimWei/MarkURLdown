from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markdownall.core.handlers import wordpress_handler as wp


@pytest.mark.unit
def test_extract_wordpress_title_variants():
    html = """
    <div id='content' role='main'><h1 class='entry-title'>WT</h1></div>
    """
    soup = BeautifulSoup(html, "lxml")
    assert wp._extract_wordpress_title(soup) == "WT"
    soup2 = BeautifulSoup("<title>ABC - Site</title>", "lxml")
    assert wp._extract_wordpress_title(soup2) == "ABC"


@pytest.mark.unit
def test_extract_wordpress_metadata():
    html = """
    <div class='author vcard'><a>AuthorZ</a></div>
    <time class='entry-date' datetime='2025-01-01'>ignored</time>
    <div class='entry-categories'><a>Cat1</a></div>
    <div class='entry-tags'><a>tag1</a></div>
    """
    soup = BeautifulSoup(html, "lxml")
    meta = wp._extract_wordpress_metadata(soup)
    assert meta["author"] == "AuthorZ"
    assert meta["publish_time"] == "2025-01-01"
    assert meta["categories"] == "Cat1"
    assert meta["tags"] == "tag1"


@pytest.mark.unit
def test_build_wordpress_header_parts_and_content_element():
    html = """
    <html><body>
      <div id='content' role='main'>
        <h1 class='entry-title'>TitleW</h1>
        <div class='entry-content'><p>Body</p></div>
      </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    title, parts = wp._build_wordpress_header_parts(soup, url="https://u")
    assert title == "TitleW"
    head = "\n".join(parts)
    assert "# TitleW" in head and ("来源：https://u" in head or "来源: https://u" in head)
    content = wp._build_wordpress_content_element(soup)
    assert content and content.get_text(strip=True) == "Body"


@pytest.mark.unit
def test_clean_and_normalize_wordpress_content():
    html = """
    <div id='m'>
      <img data-src='https://a/img.jpg'>
      <img data-original='https://b/img.png'>
      <script>bad()</script><style>.x{}</style>
      <div class='advertisement'>ad</div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    elem = soup.find(id="m")
    wp._clean_and_normalize_wordpress_content(elem)
    s = str(elem)
    assert "data-src" not in s and "data-original" not in s
    assert "<script" not in s and "advertisement" not in s
