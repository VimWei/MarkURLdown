from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from markdownall.core.handlers import weixin_handler as wx


@pytest.mark.unit
def test_build_weixin_header_parts_extracts_fields():
    html = """
    <html>
      <body>
        <h1 class="rich_media_title" id="activity-name">标题A</h1>
        <div id="meta_content">
          <span class="rich_media_meta rich_media_meta_text">作者X</span>
          <em id="publish_time" class="rich_media_meta rich_media_meta_text">2025-09-30</em>
          <em id="js_ip_wording_wrp"><span id="js_ip_wording">北京</span></em>
        </div>
        <span class="rich_media_meta_nickname" id="profileBt"><a id="js_name">公众号Y</a></span>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    title, account, parts = wx._build_weixin_header_parts(soup, url="https://u", title_hint=None)
    assert title == "标题A"
    assert account == "公众号Y"
    header = "\n".join(parts)
    assert "# 标题A" in header and "来源：https://u" in header
    assert "作者X" in header and "2025-09-30" in header and "北京" in header


@pytest.mark.unit
def test_build_weixin_content_element_fallbacks():
    soup = BeautifulSoup("<div id='js_content'>C</div>", "lxml")
    elem = wx._build_weixin_content_element(soup)
    assert elem.get_text() == "C"


@pytest.mark.unit
def test_apply_removal_rules_by_style_class_id():
    html = """
    <div>
      <section style="border-width: 3px; color: #fff">should remove by style</section>
      <div class="qr_code_pc qr_code_pc_inner">ad</div>
      <div id="ad-banner">ad2</div>
      <p class="keep">stay</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    rules = [
        {"tag": "section", "styles": ["border-width: 3px"]},
        {"tag": "div", "classes": ["qr_code_pc", "qr_code_pc_inner"]},
        {"tag": "div", "ids": ["ad-banner"]},
    ]
    wx._apply_removal_rules(soup, rules)
    s = str(soup)
    assert "should remove" not in s
    assert "ad</div>" not in s
    assert "ad2" not in s
    assert "stay" in s


@pytest.mark.unit
def test_get_account_specific_style_rules_merges_general():
    rules_general = wx._get_account_specific_style_rules(None)
    assert isinstance(rules_general, list) and rules_general
    rules_acc = wx._get_account_specific_style_rules("央视财经")
    # account-specific adds more rules
    assert len(rules_acc) >= len(rules_general)


@pytest.mark.unit
def test_clean_and_normalize_replaces_lazy_images_and_removes_scripts():
    html = """
    <div id='js_content'>
      <img data-src="https://a/img.jpg"><script>bad()</script><style>.x{}</style>
      <img data-original="https://b/img.png">
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    content = soup.find("div", id="js_content")
    wx._clean_and_normalize_weixin_content(content, account_name=None)
    out = str(content)
    assert "data-src" not in out and "data-original" not in out
    assert 'src="https://a/img.jpg"' in out
    assert 'src="https://b/img.png"' in out
    assert "<script" not in out and "<style" not in out


@pytest.mark.unit
def test_process_weixin_content_builds_header_and_md():
    html = """
    <html><body>
      <h1 class="rich_media_title" id="activity-name">标题Z</h1>
      <div id="meta_content"><span class="rich_media_meta rich_media_meta_text">作者A</span></div>
      <span class="rich_media_meta_nickname" id="profileBt"><a id="js_name">号B</a></span>
      <div class="rich_media_content"><p>正文</p></div>
    </body></html>
    """
    res = wx._process_weixin_content(html, title=None, url="https://u")
    assert res.title == "标题Z"
    # 标题行、来源与作者信息应在正文前
    assert res.html_markdown.startswith("# 标题Z\n")
    assert "来源：https://u" in res.html_markdown
    assert "作者A" in res.html_markdown and "号B" in res.html_markdown
    assert res.html_markdown.strip().endswith("正文")
