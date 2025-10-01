from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markurldown.core.handlers import sspai_handler as sp


@pytest.mark.unit
def test_extract_title_variants():
    soup = BeautifulSoup("<h1 class='post-title'>Title A</h1>", "lxml")
    assert sp._extract_sspai_title(soup) == "Title A"
    soup2 = BeautifulSoup("<title>Another - 少数派</title>", "lxml")
    assert sp._extract_sspai_title(soup2) == "Another"
    soup3 = BeautifulSoup("<title>Case - Site</title>", "lxml")
    assert sp._extract_sspai_title(soup3) == "Case"


@pytest.mark.unit
def test_extract_metadata_basic():
    html = """
    <div class='article-author'><div class='author-box'><div><span><span><div><a><div><span>AuthorX</span></div></a></div></span></span></div></div></div>
    <time class='timer' datetime='2025-01-01'>ignored</time>
    <div class='series-title'><a>Cat1</a><a>Cat2</a></div>
    <div class='entry-tags'><a>tag1</a><a>tag2</a></div>
    """
    soup = BeautifulSoup(html, "lxml")
    meta = sp._extract_sspai_metadata(soup)
    assert meta["author"] == "AuthorX"
    assert meta["publish_time"] == "2025-01-01"
    assert meta["categories"] == "Cat1, Cat2"
    assert meta["tags"] == "tag1, tag2"


@pytest.mark.unit
def test_build_header_parts_and_content_element():
    html = """
    <html><body>
      <h1 class='entry-title'>TitleZ</h1>
      <div class='article-author'><div class='author-box'><div><span><span><div><span>Writer</span></div></span></span></div></div></div>
      <div class='series-title'><a>Cat</a></div>
      <div class='entry-tags'><a>t</a></div>
      <article>
        <div class='article-body'>
          <div class='article__main__content wangEditor-txt'><p>Body</p></div>
        </div>
      </article>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    title, parts = sp._build_sspai_header_parts(soup, url="https://u", title_hint=None)
    assert title == "TitleZ"
    head = "\n".join(parts)
    assert "# TitleZ" in head and "来源：https://u" in head and "Writer" in head
    content = sp._build_sspai_content_element(soup)
    assert content and content.get_text(strip=True) == "Body"


@pytest.mark.unit
def test_preprocess_inline_sup_footnotes_and_strip_invisible():
    html = """
    <div id='c'>
      <p>Text<sup class='ss-footnote' footnote-id='1' title='footnote text'></sup></p>
      <p>ZWSP</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    elem = soup.find(id="c")
    m = sp._preprocess_inline_sup_footnotes(elem)
    assert m.get("1") == "footnote text"
    sp._strip_invisible_characters(elem)
    text = elem.get_text()
    assert "footnote text" in text and "ZWSP" in text


@pytest.mark.unit
def test_clean_and_normalize_sspai_content():
    html = """
    <div id='main'>
      <img data-src='https://a/img.jpg'>
      <img data-original='https://b/img.png'>
      <img data-lazy-src='https://c/img.webp'>
      <script>bad()</script><style>.x{}</style>
      <nav>n</nav><div class='entry-meta'>m</div>
      <a href='https://sspai.com/page/client'>promo</a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    elem = soup.find(id="main")
    sp._clean_and_normalize_sspai_content(elem)
    # 验证懒加载属性移除
    for img in elem.find_all("img"):
        for a in ("data-src", "data-original", "data-lazy-src"):
            assert not img.get(a)
    # 验证脚本与样式移除
    assert elem.find("script") is None and elem.find("style") is None
    # 验证无关元素已清理
    assert not elem.select(".entry-meta")
    # 验证推广链接容器被移除
    assert not elem.select("a[href='https://sspai.com/page/client']")
