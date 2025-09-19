from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
from bs4 import BeautifulSoup
from bs4 import NavigableString
import re

from markitdown_app.core.html_to_md import html_fragment_to_markdown

# 可选：使用 Playwright driver 辅助（共享或独立浏览器均可复用这些工具）
try:
    from markitdown_app.services.playwright_driver import (
        new_context_and_page,
        teardown_context_page,
        read_page_content_and_title,
    )
except Exception:
    # 若不依赖 Playwright，可忽略导入失败
    new_context_and_page = None  # type: ignore
    teardown_context_page = None  # type: ignore
    read_page_content_and_title = None  # type: ignore


@dataclass
class CrawlerResult:
    success: bool
    title: str | None
    text_content: str
    error: str | None = None


@dataclass
class FetchResult:
    title: str | None
    html_markdown: str
    success: bool = True
    error: str | None = None


# -------------------------------
# 解析：构建 header 与正文
# -------------------------------

def _extract_appinn_title(soup: BeautifulSoup, title_hint: Optional[str] = None) -> str | None:
    """提取文章标题（针对 appinn.com 的选择器优先级）。"""
    title: str | None = None

    # 针对 appinn.com 的标题选择器
    title_selectors = [
        'div.single_post header h1.title.single-title.entry-title',
    ]
    
    for sel in title_selectors:
        node = soup.select_one(sel)
        if node:
            title = node.get_text(strip=True)
            break

    if not title and title_hint:
        title = title_hint

    if not title:
        node = soup.find('title')
        if node:
            candidate = node.get_text(strip=True)
            # 移除 appinn.com 的站点后缀
            if ' - 小众软件' in candidate:
                title = candidate.replace(' - 小众软件', '')
            elif ' - Appinn' in candidate:
                title = candidate.replace(' - Appinn', '')
            else:
                title = candidate.split(' - ')[0] if ' - ' in candidate else candidate

    return title


def _extract_appinn_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    """提取元数据（作者、发布时间、分类、标签）。"""
    md: dict[str, str | None] = {
        'author': None,
        'publish_time': None,
        'categories': None,
        'tags': None,
    }

    # 作者 - 针对 appinn.com 的选择器
    for sel in [
        'div.single_post > header > div > span.theauthor > span > a',
    ]:
        node = soup.select_one(sel)
        if node:
            link = node.find('a')
            md['author'] = (link.get_text(strip=True) if link else node.get_text(strip=True)) or None
            break

    # 时间 - 针对 appinn.com 的选择器
    for sel in [
        'div.single_post > header > div > span.thetime.updated > span',
    ]:
        node = soup.select_one(sel)
        if node:
            md['publish_time'] = (node.get('datetime') or node.get_text(strip=True)) or None
            break

    # 分类 - 针对 appinn.com 的选择器
    categories: list[str] = []
    # for sel in [
    #     'div.single_post > div.breadcrumb > div:nth-child(4) > a > span',
    # ]:
    #     for el in soup.select(sel):
    #         txt = el.get_text(strip=True)
    #         if txt and txt not in categories:
    #             categories.append(txt)
    if categories:
        md['categories'] = ' '.join(categories)

    # 标签 - 针对 appinn.com 的选择器
    tags: list[str] = []
    for sel in [
        'div.single_post header div.post-info span.thecategory a',
    ]:
        for el in soup.select(sel):
            txt = el.get_text(strip=True)
            if txt and txt not in tags:
                tags.append(txt)
    if tags:
        md['tags'] = ' '.join(tags)

    return md


def _build_appinn_header_parts(soup: BeautifulSoup, url: Optional[str] = None, title_hint: Optional[str] = None) -> tuple[str | None, list[str]]:
    """构建Markdown头部信息片段（标题、来源、作者、时间等），并返回 (title, parts)。"""
    parts: list[str] = []

    title = _extract_appinn_title(soup, title_hint)
    if title:
        parts.append(f"# {title}")

    if url:
        parts.append(f"* 来源：{url}")

    md = _extract_appinn_metadata(soup)
    if any([md['author'], md['publish_time'], md['categories'], md['tags']]):
        meta_parts: list[str] = []
        if md['author']:
            meta_parts.append(f"{md['author']}")
        if md['publish_time']:
            meta_parts.append(f"{md['publish_time']}")
        if md['categories']:
            meta_parts.append(f"{md['categories']}")
        if md['tags']:
            meta_parts.append(f"{md['tags']}")
        if meta_parts:
            parts.append("* " + "  ".join(meta_parts))

    return title, parts


def _build_appinn_content_element(soup: BeautifulSoup):
    """定位并返回正文容器元素（针对 appinn.com 的选择器优先级）。"""
    content_elem = None
    
    # 针对 appinn.com 的正文容器选择器
    candidates = [
        'div.entry-content',  # 主要正文容器
        'div.post-content',
        'article .entry-content',
        'article .content',
        'article',
        'main .entry-content',
        'main .content',
        'main article',
        'main',
        '.content',
        '.post-body',
        '.entry-body'
    ]
    
    for sel in candidates:
        content_elem = soup.select_one(sel)
        if content_elem:
            break
    
    return content_elem


# -------------------------------
# 文本预处理工具：清理不可见字符
# -------------------------------

def _strip_invisible_characters(content_elem):
    """移除内容中的不可见字符（如零宽空格），以避免转为Markdown后产生空行。"""
    invisible_chars_pattern = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u00a0\u2028\u2029]")
    for text_node in list(content_elem.find_all(string=True)):
        original_text = str(text_node)
        cleaned_text = invisible_chars_pattern.sub("", original_text)
        if cleaned_text != original_text:
            cleaned_text_stripped = cleaned_text.strip()
            if cleaned_text_stripped == "":
                text_node.extract()
            else:
                text_node.replace_with(cleaned_text)


# -------------------------------
# 清理与规范化：仅对子集做有界处理
# -------------------------------

def _clean_and_normalize_appinn_content(content_elem) -> None:
    """清洗与标准化 appinn.com 正文容器"""
    if not content_elem:
        return

    # 懒加载图片归一（支持常见属性）
    lazy_src_attrs = ['data-src', 'data-original', 'data-lazy-src']
    for img in content_elem.find_all('img'):
        try:
            for a in lazy_src_attrs:
                if img.get(a):
                    img['src'] = img[a]
                    try:
                        del img[a]
                    except Exception:
                        pass
                    break
        except Exception:
            pass

    # 移除重复的图片标签（基于 src 属性去重）
    seen_srcs = set()
    for img in content_elem.find_all('img'):
        src = img.get('src', '')
        if src in seen_srcs:
            # 移除重复的图片标签
            img.decompose()
        else:
            seen_srcs.add(src)

    # 移除脚本和样式
    for node in content_elem.find_all(['script', 'style']):
        try:
            node.decompose()
        except Exception:
            pass

    # 针对 appinn.com 的"减法策略"清单
    unwanted_in_content = [
        # 导航/脚注/社交/广告/推荐/评论等
        'nav', '.nav', '.navigation', '.menu', 'header', '.header', '#header',
        'footer', '.footer', '.site-footer',
        '.social', '.social-links', '.share', '.share-buttons', '.social-media', '.social-share',
        '.related-posts', '.more-posts', '.related', '.similar-posts',
        '.post-navigation', '.nav-links', '.page-links',
        '.comments', '#comments', '.comment', '.comment-list', '.comment-form',
        # 元信息在正文中重复的
        '.entry-meta', '.post-meta', '.meta', '.meta-info',
        # 无关元素
        '.screen-reader-text', '.sr-only', '.skip-link', '.loading', '.spinner', '.placeholder',
        # 进一步收敛
        '.advertisement', '.ad', '.ads', '.advertisement-container',
        '.recommendation', '.recommended', '.related-articles',
        '.entry-footer', '.post-footer', '.author-bio', '.author-info',
        # appinn.com 特定的元素
        '.entry-header', '.post-header',  # 头部信息已在 header_parts 中处理
        '.breadcrumb', '.breadcrumbs',  # 面包屑导航
        '.sidebar', '.widget', '.widget-area',  # 侧边栏
        '.entry-tags', '.post-tags',  # 标签（已在 header 中处理）
        '.entry-categories', '.post-categories',  # 分类（已在 header 中处理）
    ]
    
    for sel in unwanted_in_content:
        for el in content_elem.select(sel):
            try:
                el.decompose()
            except Exception:
                pass

    _strip_invisible_characters(content_elem)


# -------------------------------
# 一体化处理：解析→清理→转换→组装
# -------------------------------

def _process_appinn_content(html: str, url: Optional[str] = None, title_hint: Optional[str] = None) -> FetchResult:
    """处理 appinn.com 内容，提取标题、元数据和过滤后的正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 构建头部信息（包含标题抽取）
    title, header_parts = _build_appinn_header_parts(soup, url, title_hint)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 正文：定位并构建正文容器
    content_elem = _build_appinn_content_element(soup)

    # 清洗与标准化正文
    if content_elem:
        _clean_and_normalize_appinn_content(content_elem)
        try:
            md_body = html_fragment_to_markdown(content_elem)
        except Exception:
            # 兜底：使用最小手动转换
            md_body = content_elem.get_text("\n", strip=False)
    else:
        md_body = ""

    # 最后拼接为全文
    if header_str:
        md = header_str + md_body if md_body else header_str
    else:
        md = md_body

    try:
        return FetchResult(title=title, html_markdown=md)
    except Exception as e:
        print(f"创建FetchResult失败: {e}")
        return FetchResult(title=None, html_markdown="")


# -------------------------------
# 抓取策略：httpx / Playwright
# -------------------------------

def _try_httpx_crawler(session, url: str) -> FetchResult:
    """策略1: 使用httpx爬取原始HTML"""
    try:
        import httpx
        headers = {
            "User-Agent": session.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        }
        client_kwargs = {"headers": headers}
        if hasattr(session, 'trust_env') and not getattr(session, 'trust_env'):
            client_kwargs["trust_env"] = False

        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return FetchResult(title=None, html_markdown=resp.text)
    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"httpx异常: {e}")


def _try_playwright_crawler(url: str, on_detail=None, shared_browser: Any | None = None) -> FetchResult:
    """策略2: 使用Playwright爬取原始HTML - 支持共享浏览器"""
    try:
        from playwright.sync_api import sync_playwright

        # 共享浏览器路径
        if shared_browser is not None and new_context_and_page is not None:
            context, page = new_context_and_page(shared_browser, apply_stealth=False)
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(2000)
                if callable(on_detail):
                    try:
                        on_detail(page)
                    except Exception:
                        pass
                if read_page_content_and_title is not None:
                    html, title = read_page_content_and_title(page)
                else:
                    html, title = page.content(), page.title()
                return FetchResult(title=title, html_markdown=html)
            finally:
                if teardown_context_page is not None:
                    teardown_context_page(context, page)
                else:
                    try:
                        context.close()
                    except Exception:
                        pass

        # 独立浏览器兜底
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            if callable(on_detail):
                try:
                    on_detail(page)
                except Exception:
                    pass
            html, title = page.content(), page.title()
            browser.close()
            return FetchResult(title=title, html_markdown=html)

    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"Playwright异常: {e}")


# -------------------------------
# 主入口：appinn.com 文章获取（含重试）
# -------------------------------

def fetch_appinn_article(session, url: str, on_detail=None, shared_browser: Any | None = None, min_content_length: int = 200) -> FetchResult:
    """获取 appinn.com 文章内容（多策略爬取 + 统一内容处理）。

    参数:
    - on_detail: 可选 Playwright 回调，在页面稳定后调用以执行细化操作。
    - shared_browser: 共享浏览器实例（如有）。
    - min_content_length: 内容质量阈值（字符数），过短则继续尝试其他策略。
    """
    strategies = [
        lambda: _try_httpx_crawler(session, url),
        lambda: _try_playwright_crawler(url, on_detail, shared_browser),
    ]

    max_retries = 2
    for i, strat in enumerate(strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    import time, random
                    print(f"尝试 appinn.com 策略 {i} (重试 {retry}/{max_retries-1})...")
                    time.sleep(random.uniform(2, 4))
                else:
                    print(f"尝试 appinn.com 策略 {i}...")

                r = strat()
                if r.success:
                    # 统一处理：策略层只负责获取HTML，这里统一解析/清理/转换
                    if r.html_markdown:
                        processed = _process_appinn_content(r.html_markdown, url, title_hint=r.title)
                        # 检查内容质量，如果内容太短，继续尝试下一个策略
                        content = processed.html_markdown or ""
                        if len(content) < max(0, int(min_content_length)):
                            print(f"appinn.com 策略 {i} 内容太短 ({len(content)} 字符)，继续尝试下一个策略")
                            break
                        return processed
                    else:
                        return r
                else:
                    print(f"策略 {i} 失败: {r.error}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                        break
            except Exception as e:
                print(f"策略 {i} 异常: {e}")
                if retry < max_retries - 1:
                    continue
                else:
                    print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                    break

        # 策略间等待
        if i < len(strategies):
            import time, random
            time.sleep(random.uniform(1, 2))

    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")
