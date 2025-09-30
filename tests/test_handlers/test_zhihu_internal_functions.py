from __future__ import annotations

from bs4 import BeautifulSoup
import types
import pytest

from markitdown_app.core.handlers import zhihu_handler as zh


@pytest.mark.unit
def test_detect_page_type_answer_and_column():
    a = zh._detect_zhihu_page_type("https://www.zhihu.com/question/1/answer/2")
    assert a.is_answer_page and a.kind == "answer"
    c = zh._detect_zhihu_page_type("https://zhuanlan.zhihu.com/p/123")
    assert c.is_column_page and c.kind == "column"


@pytest.mark.unit
def test_extract_title_and_author_and_time():
    soup = BeautifulSoup("""
    <h1 class='QuestionHeader-title'>Answer Title</h1>
    <div class='ContentItem-meta'><a class='UserLink-link' href='/people/u1'>User</a><div class='AuthorInfo-detail'><span class='AuthorInfo-badgeText'>badge</span></div></div>
    <div class='ContentItem-time'>编辑于 2023-07-13 23:39 ・江苏</div>
    """, "lxml")
    pt = zh._detect_zhihu_page_type("https://www.zhihu.com/question/1/answer/2")
    assert zh._extract_zhihu_title(soup, pt) == "Answer Title"
    name, href, badge = zh._extract_zhihu_author(soup, pt)
    assert name == "User" and href.endswith("/people/u1") and badge == "badge"
    t = zh._extract_zhihu_time(soup, pt)
    assert "2023-07-13" in t


@pytest.mark.unit
def test_link_normalization_and_redirect_cleanup():
    soup = BeautifulSoup("""
    <div id='c'>
      <a href='//www.zhihu.com/p/1'>rel</a>
      <a href='/question/1/answer/2'>rel2</a>
      <a href='https://link.zhihu.com/?target=https%3A%2F%2Fexample.com'>redir</a>
      <a href='https://zhida.zhihu.com/search?xx=1'>直答</a>
    </div>
    """, "lxml")
    c = soup.find(id='c')
    zh._clean_zhihu_external_links(c)
    zh._normalize_zhihu_links(c)
    zh._clean_zhihu_zhida_links(c)
    s = str(c)
    assert "https://example.com" in s
    # After cleanup, internal links may be converted to plain text; assert text present
    assert "rel2" in s
    assert "直答" in s and "zhida.zhihu.com" not in s


@pytest.mark.unit
def test_clean_and_normalize_zhihu_content_handles_images_and_links():
    html = """
    <div class="RichContent-inner">
        <figure>
            <img src="data:image/svg+xml;base64,xxx" />
            <noscript><img src="https://img.example/a.jpg" /></noscript>
            <img data-src="https://img.example/dup.jpg" />
            <img data-original="https://img.example/dup.jpg" />
        </figure>
        <script>void 0</script>
        <style>h1{}</style>
        <a href="//www.zhihu.com/abc">x</a>
        <a href="/p/123">y</a>
        <a href="https://zhida.zhihu.com/search?foo=1">直答</a>
        <a href="https://www.zhihu.com/question/1/answer/2">内部</a>
        <a href="https://link.zhihu.com/?target=https%3A%2F%2Fexample.com%2Fr">外链</a>
        <span>word\u200b</span>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    elem = soup.select_one(".RichContent-inner")
    page_type = zh.ZhihuPageType(is_answer_page=True, is_column_page=False, kind="answer")
    zh._clean_and_normalize_zhihu_content(elem, page_type, soup)

    # Within <figure>, logic keeps noscript img and removes others; scripts/styles removed
    imgs = elem.find_all("img")
    assert len(imgs) == 1
    srcs = [i.get("src") for i in imgs]
    assert srcs == ["https://img.example/a.jpg"]

    # zhida/internal links converted to text
    assert not elem.find("a", href=lambda h: h and "zhida.zhihu.com" in h)
    assert not elem.find("a", href=lambda h: h and "/question/" in h)

    # external redirect link decoded to original
    a = elem.find("a", href=lambda h: h and h.startswith("https://example.com/r"))
    assert a is not None

    # site-root and protocol-relative normalized to absolute
    assert not elem.find("a", href="/p/123")
    assert not elem.find("a", href="//www.zhihu.com/abc")

    # invisible chars stripped
    assert "\u200b" not in elem.get_text()


@pytest.mark.unit
def test_apply_zhihu_stealth_and_try_click_buttons():
    class Btn:
        def __init__(self):
            self._visible = True
        def is_visible(self):
            return True
        def scroll_into_view_if_needed(self):
            return None
        def click(self, timeout=3000):
            return None
    class Page:
        def __init__(self):
            self.scripts = []
            self.timeout = None
        def add_init_script(self, js):
            self.scripts.append(js)
        def set_default_timeout(self, ms):
            self.timeout = ms
        def query_selector_all(self, selector):
            return [Btn()]
        def wait_for_timeout(self, ms):
            return None
    p = Page()
    zh._apply_zhihu_stealth_and_defaults(p, default_timeout_ms=12345)
    assert p.scripts and p.timeout == 12345
    assert zh._try_click_expand_buttons(p) is True


@pytest.mark.unit
def test_build_zhihu_content_element_by_page_type():
    # Answer page: prefers RichContent-inner
    soup_answer = BeautifulSoup("""
    <div class='RichContent RichContent--unescapable'>
      <div class='RichContent-inner'><p>ans</p></div>
    </div>
    """, "lxml")
    pt_answer = zh.ZhihuPageType(is_answer_page=True, is_column_page=False, kind="answer")
    elem_ans = zh._build_zhihu_content_element(soup_answer, pt_answer)
    assert elem_ans and elem_ans.get("class") and "RichContent-inner" in " ".join(elem_ans.get("class"))

    # Column page: prefers Post-RichTextContainer
    soup_col = BeautifulSoup("""
    <div class='Post-RichTextContainer'><article>col</article></div>
    """, "lxml")
    pt_col = zh.ZhihuPageType(is_answer_page=False, is_column_page=True, kind="column")
    elem_col = zh._build_zhihu_content_element(soup_col, pt_col)
    assert elem_col and elem_col.get("class") and "Post-RichTextContainer" in " ".join(elem_col.get("class"))

    # Unknown page: returns None
    soup_unknown = BeautifulSoup("<div><p>u</p></div>", "lxml")
    pt_unknown = zh.ZhihuPageType(is_answer_page=False, is_column_page=False, kind="unknown")
    assert zh._build_zhihu_content_element(soup_unknown, pt_unknown) is None


@pytest.mark.unit
def test_get_wait_selector_for_page_type():
    a = zh._detect_zhihu_page_type("https://www.zhihu.com/question/1/answer/2")
    c = zh._detect_zhihu_page_type("https://zhuanlan.zhihu.com/p/1")
    u = zh._detect_zhihu_page_type("https://unknown")
    assert zh._get_wait_selector_for_page_type(a) in zh.WAIT_SELECTOR_BY_TYPE.values()
    assert zh._get_wait_selector_for_page_type(c) in zh.WAIT_SELECTOR_BY_TYPE.values()
    assert zh._get_wait_selector_for_page_type(u) in zh.WAIT_SELECTOR_BY_TYPE.values()


@pytest.mark.unit
def test_zhihu_try_playwright_crawler_shared_success(monkeypatch):
    page = types.SimpleNamespace(
        goto=lambda *a, **k: None,
        wait_for_timeout=lambda ms: None,
    )
    context = types.SimpleNamespace(new_page=lambda: page)
    # patch helpers
    monkeypatch.setattr(zh, 'new_context_and_page', lambda b, apply_stealth=False: (context, page))
    monkeypatch.setattr(zh, '_apply_zhihu_stealth_and_defaults', lambda p: None)
    monkeypatch.setattr(zh, '_goto_target_and_prepare_content', lambda p, url, on_detail=None: None)
    monkeypatch.setattr(zh, 'read_page_content_and_title', lambda p, on_detail=None: ("<html>OK</html>", "T"))
    monkeypatch.setattr(zh, 'teardown_context_page', lambda c, p: None)
    r = zh._try_playwright_crawler("https://www.zhihu.com/question/1/answer/2", on_detail=None, shared_browser=object())
    assert r.success and r.text_content.startswith("<html>")


