from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markdownall.core.handlers import appinn_handler as ap


@pytest.mark.unit
def test_extract_appinn_title_variants():
    soup = BeautifulSoup(
        "<div class='single_post'><header><h1 class='title single-title entry-title'>T</h1></header></div>",
        "lxml",
    )
    assert ap._extract_appinn_title(soup) == "T"
    soup2 = BeautifulSoup("<title>X - 小众软件</title>", "lxml")
    assert ap._extract_appinn_title(soup2) == "X"
    soup3 = BeautifulSoup("<title>Y - Appinn</title>", "lxml")
    assert ap._extract_appinn_title(soup3) == "Y"


@pytest.mark.unit
def test_extract_appinn_metadata():
    html = """
    <div class='single_post'>
      <header>
        <div>
          <span class='theauthor'><span><a>Author1</a></span></span>
          <span class='thetime updated'><span datetime='2025-01-01'>ignored</span></span>
          <div class='post-info'><span class='thecategory'><a>tagA</a><a>tagB</a></span></div>
        </div>
      </header>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    md = ap._extract_appinn_metadata(soup)
    assert md["author"] == "Author1"
    assert md["publish_time"] == "2025-01-01"
    assert md["tags"] == "tagA tagB"


@pytest.mark.unit
def test_build_appinn_header_parts_and_content_element():
    html = """
    <div class='single_post'>
      <header><h1 class='title single-title entry-title'>T2</h1></header>
      <div class='post-info'><span class='thecategory'><a>tagA</a></span></div>
      <div class='entry-content'><p>Body</p></div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    title, parts = ap._build_appinn_header_parts(soup, url="https://u")
    assert title == "T2"
    head = "\n".join(parts)
    # Allow either full-width colon or normal colon depending on environment
    assert "# T2" in head and ("来源：https://u" in head or "来源: https://u" in head)
    content = ap._build_appinn_content_element(soup)
    assert content and content.get_text(strip=True) == "Body"


@pytest.mark.unit
def test_clean_and_normalize_appinn_content():
    html = """
    <div id='m'>
      <img data-src='https://a/img.jpg'>
      <img data-original='https://b/img.png'>
      <img data-lazy-src='https://c/img.webp'>
      <img src='https://b/img.png'>
      <script>bad()</script><style>.x{}</style>
      <div class='entry-meta'>m</div><div class='advertisement'>ad</div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    elem = soup.find(id="m")
    ap._clean_and_normalize_appinn_content(elem)
    s = str(elem)
    assert "data-src" not in s and "data-original" not in s and "data-lazy-src" not in s
    # three unique src after dedup: a, b, c
    assert s.count("<img") == 3
    assert "<script" not in s and "advertisement" not in s and "entry-meta" not in s
