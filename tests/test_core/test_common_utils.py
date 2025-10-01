from __future__ import annotations

import pytest

from markurldown.core.common_utils import (
    COMMON_FILTERS,
    DOMAIN_FILTERS,
    apply_dom_filters,
    extract_title_from_body,
    extract_title_from_html,
    get_user_agents,
)


@pytest.mark.unit
def test_common_filters_contains_key_categories():
    # spot check some categories exist
    assert "head" in COMMON_FILTERS
    assert "nav" in COMMON_FILTERS and ".footer" in COMMON_FILTERS
    assert ".toc" in COMMON_FILTERS and ".ads" in COMMON_FILTERS


@pytest.mark.unit
def test_domain_filters_has_juejin_keys():
    assert "juejin.cn" in DOMAIN_FILTERS
    assert any("header" in s for s in DOMAIN_FILTERS["juejin.cn"])


@pytest.mark.unit
def test_apply_dom_filters_removes_elements_and_counts():
    html = """
    <html><head><title>t</title></head>
    <body>
      <nav>n1</nav>
      <div class="footer">f1</div>
      <article><p>content</p></article>
    </body></html>
    """
    out, removed = apply_dom_filters(html, ["nav", ".footer"])
    assert removed == 2
    assert "n1" not in out and "f1" not in out
    assert "content" in out


@pytest.mark.unit
def test_get_user_agents_non_empty_and_diverse():
    uas = get_user_agents()
    assert isinstance(uas, list) and len(uas) >= 3
    # ensure包含不同浏览器标识
    joined = "\n".join(uas)
    assert "Chrome" in joined and ("Firefox" in joined or "Safari" in joined)


@pytest.mark.unit
def test_extract_title_from_html_handles_missing_and_error():
    html = "<html><head><title>My Site - Suffix</title></head><body></body></html>"
    title = extract_title_from_html(html)
    # extract_title_from_html does not strip suffix; body extractor will
    assert title == "My Site - Suffix"

    # invalid/malformed html should not raise
    assert extract_title_from_html(None) is None  # type: ignore[arg-type]


@pytest.mark.unit
def test_extract_title_from_body_priority_and_cleanup():
    html = """
    <html>
      <head><title>Ignore me</title></head>
      <body>
        <header>Header</header>
        <main>
          <h1 class="article-title">My Article - SomeSite</h1>
          <article><h1>Other</h1></article>
        </main>
      </body>
    </html>
    """
    title = extract_title_from_body(html)
    assert title == "My Article"

    # fallback to plain h1 when specific selectors missing
    html2 = "<html><body><h1>Plain Title - Site</h1></body></html>"
    assert extract_title_from_body(html2) == "Plain Title"

    # malformed should return None
    assert extract_title_from_body(None) is None  # type: ignore[arg-type]
