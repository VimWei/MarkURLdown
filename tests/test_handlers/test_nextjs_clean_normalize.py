from __future__ import annotations

from bs4 import BeautifulSoup

from markdownall.core.handlers.nextjs_handler import _clean_and_normalize_nextjs_content


def _make_soup(html: str):
    return BeautifulSoup(html, "lxml")


def test_nextjs_clean_normalize_handles_lazy_images_and_removes_unwanted():
    html = """
        <div id="content">
          <h1>Title Should Be Removed</h1>
          <nav>nav</nav>
          <aside class="sidebar">sb</aside>
          <p class="text-sm">meta</p>
          <div class="on-this-page">toc</div>
          <img data-src="https://x/img1.png" />
          <img data-original="https://x/img2.png" />
          <img src="https://x/img3.png" />
          <script>var a=1;</script>
          <style>body{}</style>
          <p>Keep me</p>
        </div>
        """
    soup = _make_soup(html)
    content = soup.find(id="content")
    _clean_and_normalize_nextjs_content(content)

    # h1, nav, aside.sidebar, p.text-sm, on-this-page should be removed
    assert content.find("h1") is None
    assert content.find("nav") is None
    assert content.select_one(".sidebar") is None
    assert content.select_one("p.text-sm") is None
    assert content.select_one(".on-this-page") is None

    # script/style removed
    assert content.find("script") is None
    assert content.find("style") is None

    # lazy images fixed
    imgs = content.find_all("img")
    srcs = [img.get("src") for img in imgs]
    assert (
        "https://x/img1.png" in srcs
        and "https://x/img2.png" in srcs
        and "https://x/img3.png" in srcs
    )
    # data-src and data-original removed where present
    for img in imgs:
        assert "data-src" not in img.attrs
        assert "data-original" not in img.attrs


def test_nextjs_clean_normalize_noop_on_none():
    # Should not raise
    _clean_and_normalize_nextjs_content(None)
