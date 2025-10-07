from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from bs4 import BeautifulSoup, NavigableString

from markdownall.core.html_to_md import html_fragment_to_markdown

# 可选：使用 Playwright driver 辅助（共享或独立浏览器均可复用这些工具）
try:
    from markdownall.services.playwright_driver import (
        new_context_and_page,
        read_page_content_and_title,
        teardown_context_page,
    )
    from markdownall.app_types import ConvertLogger
except Exception:
    # 若不依赖 Playwright，可忽略导入失败
    new_context_and_page = None  # type: ignore
    teardown_context_page = None  # type: ignore
    read_page_content_and_title = None  # type: ignore
    ConvertLogger = None  # type: ignore


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


def _extract_newsite_title(soup: BeautifulSoup, title_hint: Optional[str] = None) -> str | None:
    """提取文章标题（可按站点定制选择器优先级）。"""
    title: str | None = None

    title_selectors = [
        "article h1",
        "main h1",
        ".entry-content h1",
        ".post h1",
        ".post-title",
        ".page-title",
        ".article-title",
        "h1",
    ]
    for sel in title_selectors:
        node = soup.select_one(sel)
        if node:
            title = node.get_text(strip=True)
            break

    if not title and title_hint:
        title = title_hint

    if not title:
        node = soup.find("title")
        if node:
            candidate = node.get_text(strip=True)
            title = candidate.split(" - ")[0] if " - " in candidate else candidate

    return title


def _extract_newsite_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    """提取元数据（作者、发布时间、分类、标签）。可按站点扩展选择器。"""
    md: dict[str, str | None] = {
        "author": None,
        "publish_time": None,
        "categories": None,
        "tags": None,
    }

    # 作者
    for sel in [
        ".author",
        ".post-author",
        ".entry-author",
        ".byline",
        ".author-name",
        ".meta-author",
        ".post-meta .author",
    ]:
        node = soup.select_one(sel)
        if node:
            link = node.find("a")
            md["author"] = (
                link.get_text(strip=True) if link else node.get_text(strip=True)
            ) or None
            break

    # 时间
    for sel in [
        "time[datetime]",
        ".publish-date",
        ".post-date",
        ".entry-date",
        ".date",
        ".meta-date",
        ".post-meta .date",
    ]:
        node = soup.select_one(sel)
        if node:
            md["publish_time"] = (node.get("datetime") or node.get_text(strip=True)) or None
            break

    # 分类
    categories: list[str] = []
    for sel in [
        ".entry-categories a",
        ".post-categories a",
        ".categories a",
        ".cat-links a",
        'a[rel="category"]',
    ]:
        for el in soup.select(sel):
            txt = el.get_text(strip=True)
            if txt and txt not in categories:
                categories.append(txt)
    if categories:
        md["categories"] = ", ".join(categories)

    # 标签
    tags: list[str] = []
    for sel in [".entry-tags a", ".post-tags a", ".tags a", ".tag-links a", 'a[rel="tag"]']:
        for el in soup.select(sel):
            txt = el.get_text(strip=True)
            if txt and txt not in tags:
                tags.append(txt)
    if tags:
        md["tags"] = ", ".join(tags)

    return md


def _build_newsite_header_parts(
    soup: BeautifulSoup, url: Optional[str] = None, title_hint: Optional[str] = None
) -> tuple[str | None, list[str]]:
    """构建Markdown头部信息片段（标题、来源、作者、时间等），并返回 (title, parts)。"""
    parts: list[str] = []

    title = _extract_newsite_title(soup, title_hint)
    if title:
        parts.append(f"# {title}")

    if url:
        parts.append(f"* 来源：{url}")

    md = _extract_newsite_metadata(soup)
    if any([md["author"], md["publish_time"], md["categories"], md["tags"]]):
        meta_parts: list[str] = []
        if md["author"]:
            meta_parts.append(f"{md['author']}")
        if md["publish_time"]:
            meta_parts.append(f"{md['publish_time']}")
        if md["categories"]:
            meta_parts.append(f"{md['categories']}")
        if md["tags"]:
            meta_parts.append(f"{md['tags']}")
        if meta_parts:
            parts.append("* " + "  ".join(meta_parts))

    return title, parts


def _build_newsite_content_element(soup: BeautifulSoup):
    """定位并返回正文容器元素（按站点定制选择器优先级）。"""
    content_elem = None
    candidates = [
        "div.entry-content",
        "div.post-content",
        "article .entry-content",
        "article .content",
        "article",
        "main .entry-content",
        "main .content",
        "main article",
        "main",
        ".content",
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
    invisible_chars_pattern = re.compile(
        r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u00a0\u2028\u2029]"
    )
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


def _clean_and_normalize_newsite_content(content_elem) -> None:
    if not content_elem:
        return

    # 懒加载图片归一（支持常见属性）
    lazy_src_attrs = ["data-src", "data-original", "data-lazy-src"]
    for img in content_elem.find_all("img"):
        try:
            for a in lazy_src_attrs:
                if img.get(a):
                    img["src"] = img[a]
                    try:
                        del img[a]
                    except Exception:
                        pass
                    break
        except Exception:
            pass

    # 移除脚本和样式
    for node in content_elem.find_all(["script", "style"]):
        try:
            node.decompose()
        except Exception:
            pass

    # 站点可定制的“减法策略”清单（建议按域名扩展覆盖）
    unwanted_in_content = [
        # 导航/脚注/社交/广告/推荐/评论等
        "nav",
        ".nav",
        ".navigation",
        ".menu",
        "header",
        ".header",
        "#header",
        "footer",
        ".footer",
        ".site-footer",
        ".social",
        ".social-links",
        ".share",
        ".share-buttons",
        ".social-media",
        ".social-share",
        ".related-posts",
        ".more-posts",
        ".related",
        ".similar-posts",
        ".post-navigation",
        ".nav-links",
        ".page-links",
        ".comments",
        "#comments",
        ".comment",
        ".comment-list",
        ".comment-form",
        # 元信息在正文中重复的
        ".entry-meta",
        ".post-meta",
        ".meta",
        ".meta-info",
        # 无关元素
        ".screen-reader-text",
        ".sr-only",
        ".skip-link",
        ".loading",
        ".spinner",
        ".placeholder",
        # 进一步收敛
        ".advertisement",
        ".ad",
        ".ads",
        ".advertisement-container",
        ".recommendation",
        ".recommended",
        ".related-articles",
        ".entry-footer",
        ".post-footer",
        ".author-bio",
        ".author-info",
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
# 注意：在实际使用中，可以在各个处理阶段添加细粒度日志：
# - logger.parse_start(): 解析开始
# - logger.parse_title(title): 解析到的标题
# - logger.parse_success(content_length): 解析成功
# - logger.clean_start(): 清理开始
# - logger.clean_success(): 清理完成
# - logger.convert_start(): 转换开始
# - logger.convert_success(): 转换完成


def _process_newsite_content(
    html: str, url: Optional[str] = None, title_hint: Optional[str] = None
) -> FetchResult:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return FetchResult(title=None, html_markdown="")

    title, header_parts = _build_newsite_header_parts(soup, url, title_hint)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    content_elem = _build_newsite_content_element(soup)

    if content_elem:
        _clean_and_normalize_newsite_content(content_elem)
        try:
            md_body = html_fragment_to_markdown(content_elem)
        except Exception:
            # 兜底：使用最小手动转换（可选实现）
            md_body = content_elem.get_text("\n", strip=False)
    else:
        md_body = ""

    md = header_str + md_body if header_str else md_body
    return FetchResult(title=title, html_markdown=md)


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
        if hasattr(session, "trust_env") and not getattr(session, "trust_env"):
            client_kwargs["trust_env"] = False

        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return FetchResult(title=None, html_markdown=resp.text)
    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"httpx异常: {e}")


def _try_playwright_crawler(
    url: str, logger: ConvertLogger | None = None, shared_browser: Any | None = None
) -> FetchResult:
    """策略2: 使用Playwright爬取原始HTML - 支持共享浏览器"""
    try:
        from playwright.sync_api import sync_playwright

        # 共享浏览器路径
        if shared_browser is not None and new_context_and_page is not None:
            context, page = new_context_and_page(shared_browser, apply_stealth=False)
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)
                if logger:
                    logger.fetch_start("playwright")
                if read_page_content_and_title is not None:
                    html, title = read_page_content_and_title(page, logger)
                else:
                    html, title = page.content(), page.title()
                if logger:
                    logger.fetch_success(len(html))
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
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            if logger:
                logger.fetch_start("playwright")
            html, title = page.content(), page.title()
            if logger:
                logger.fetch_success(len(html))
            browser.close()
            return FetchResult(title=title, html_markdown=html)

    except Exception as e:
        return FetchResult(
            title=None, html_markdown="", success=False, error=f"Playwright异常: {e}"
        )


# -------------------------------
# 主入口：新站点文章获取（含重试）
# -------------------------------
# 注意：本模板使用细粒度日志方法，提供更清晰的进度信息：
# - fetch_start(strategy_name): 记录抓取开始
# - fetch_success(content_length): 记录抓取成功
# - fetch_failed(strategy_name, error): 记录抓取失败
# - fetch_retry(strategy_name, retry, max_retries): 记录重试
# - parse_content_short(length, min_length): 记录内容太短
# - url_success(title): 记录URL处理成功
# - url_failed(url, error): 记录URL处理失败


def fetch_newsite_article(
    session,
    url: str,
    logger: ConvertLogger | None = None,
    shared_browser: Any | None = None,
    min_content_length: int = 200,
) -> FetchResult:
    """获取新站点文章内容（多策略爬取 + 统一内容处理）。

    参数:
    - logger: 可选的日志记录器，使用细粒度日志方法记录操作进度和状态。
      支持的方法包括：fetch_start(), fetch_success(), fetch_failed(), 
      fetch_retry(), parse_content_short(), url_success(), url_failed() 等。
    - shared_browser: 共享浏览器实例（如有）。
    - min_content_length: 内容质量阈值（字符数），过短则继续尝试其他策略。
    """
    strategies = [
        lambda: _try_httpx_crawler(session, url),
        lambda: _try_playwright_crawler(url, logger, shared_browser),
    ]

    max_retries = 2
    for i, strat in enumerate(strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    import random
                    import time

                    if logger:
                        logger.fetch_retry(f"策略{i}", retry, max_retries)
                    time.sleep(random.uniform(2, 4))
                else:
                    if logger:
                        logger.fetch_start(f"策略{i}")

                r = strat()
                if r.success:
                    # 统一处理：策略层只负责获取HTML，这里统一解析/清理/转换
                    if r.html_markdown:
                        processed = _process_newsite_content(
                            r.html_markdown, url, title_hint=r.title
                        )
                        # 检查内容质量，如果内容太短，继续尝试下一个策略
                        content = processed.html_markdown or ""
                        if len(content) < max(0, int(min_content_length)):
                            if logger:
                                logger.parse_content_short(len(content), min_content_length)
                            break
                        if logger:
                            logger.fetch_success(len(content))
                            logger.url_success(processed.title or "无标题")
                        return processed
                    else:
                        return r
                else:
                    if logger:
                        logger.fetch_failed(f"策略{i}", r.error or "未知错误")
                    if retry < max_retries - 1:
                        continue
                    else:
                        if logger:
                            logger.warning(f"策略 {i} 重试次数用尽，尝试下一个策略")
                        break
            except Exception as e:
                if logger:
                    logger.fetch_failed(f"策略{i}", str(e))
                if retry < max_retries - 1:
                    continue
                else:
                    if logger:
                        logger.warning(f"策略 {i} 重试次数用尽，尝试下一个策略")
                    break

        # 策略间等待
        if i < len(strategies):
            import random
            import time

            time.sleep(random.uniform(1, 2))

    if logger:
        logger.url_failed(url, "所有策略都失败")
    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")
