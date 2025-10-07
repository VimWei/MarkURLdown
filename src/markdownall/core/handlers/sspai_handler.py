"""
少数派网站处理器 - 专门处理sspai.com站点
处理文章标题、作者、发布时间、分类、标签等元数据
"""

import random
import re
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable
from markdownall.app_types import ConvertLogger

from bs4 import BeautifulSoup, NavigableString

from markdownall.services.playwright_driver import (
    new_context_and_page,
    read_page_content_and_title,
    teardown_context_page,
)
from markdownall.core.exceptions import StopRequested

# 1. 数据类


@dataclass
class FetchResult:
    """获取结果"""

    title: str | None
    html_markdown: str
    success: bool = True
    error: str | None = None


# 2. 底层工具函数（按调用关系排序）


def _extract_sspai_title(soup: BeautifulSoup, title_hint: str | None = None) -> str | None:
    """提取少数派文章标题"""
    title = None

    # 策略1: 优先查找文章标题
    title_selectors = [
        "div#article-title",
        "h1.entry-title",
        "h1.post-title",
        "article h1",
        "main h1",
        ".entry-content h1",
        ".post h1",
        ".post-title",
        "h1",
    ]

    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem:
            title = title_elem.get_text(strip=True)
            break

    # 策略2: 如果策略1没找到，使用 Playwright 获取的标题
    if not title and title_hint:
        title = title_hint

    # 策略3: 从 <title> 标签提取
    if not title:
        title_elem = soup.find("title")
        if title_elem:
            candidate = title_elem.get_text(strip=True)
            # 清理少数派标题后缀
            if " - 少数派" in candidate:
                title = candidate.replace(" - 少数派", "").strip()
            elif " - " in candidate:
                title = candidate.split(" - ")[0].strip()
            else:
                title = candidate

    return title


def _extract_sspai_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    """提取少数派文章元数据（作者、发布时间、分类、标签）"""
    metadata = {
        "author": None,
        "publish_time": None,
        "categories": None,
        "tags": None,
    }

    # 作者
    author_selectors = [
        "div.article-author > div.author-box > div > span > span > div > span",
        "div.article-author > div.author-box > div > span > span > div > a > div > span",
    ]

    for selector in author_selectors:
        author_elem = soup.select_one(selector)
        if author_elem:
            # 优先取链接文本，否则取元素文本
            link = author_elem.find("a")
            metadata["author"] = (
                link.get_text(strip=True) if link else author_elem.get_text(strip=True)
            ) or None
            break

    # 发布时间
    time_selectors = [
        ".timer",
    ]

    for selector in time_selectors:
        time_elem = soup.select_one(selector)
        if time_elem:
            metadata["publish_time"] = (
                time_elem.get("datetime") or time_elem.get_text(strip=True)
            ) or None
            break

    # 分类
    categories = []
    category_selectors = [
        ".series-title a",
    ]

    for selector in category_selectors:
        for elem in soup.select(selector):
            text = elem.get_text(strip=True)
            if text and text not in categories:
                categories.append(text)

    if categories:
        metadata["categories"] = ", ".join(categories)

    # 标签
    tags = []
    tag_selectors = [
        ".entry-tags a",
        ".post-tags a",
        ".tags a",
        ".tag-links a",
        'a[rel="tag"]',
        ".entry-meta .tags a",
        ".post-meta .tags a",
    ]

    for selector in tag_selectors:
        for elem in soup.select(selector):
            text = elem.get_text(strip=True)
            if text and text not in tags:
                tags.append(text)

    if tags:
        metadata["tags"] = ", ".join(tags)

    return metadata


def _build_sspai_header_parts(
    soup: BeautifulSoup, url: str | None = None, title_hint: str | None = None
) -> tuple[str | None, list[str]]:
    """构建少数派文章Markdown头部信息片段"""
    parts = []

    title = _extract_sspai_title(soup, title_hint)
    if title:
        parts.append(f"# {title}")

    if url:
        parts.append(f"* 来源：{url}")

    metadata = _extract_sspai_metadata(soup)
    if any(
        [metadata["author"], metadata["publish_time"], metadata["categories"], metadata["tags"]]
    ):
        meta_parts = []
        if metadata["author"]:
            meta_parts.append(f"{metadata['author']}")
        if metadata["publish_time"]:
            meta_parts.append(f"{metadata['publish_time']}")
        if metadata["categories"]:
            meta_parts.append(f"{metadata['categories']}")
        if metadata["tags"]:
            meta_parts.append(f"{metadata['tags']}")
        if meta_parts:
            parts.append("* " + " ".join(meta_parts))

    return title, parts


def _build_sspai_content_element(soup: BeautifulSoup):
    """定位并返回少数派文章正文容器元素"""
    content_elem = None
    candidates = [
        "article div.article-body div.article__main__content.wangEditor-txt",
    ]

    for selector in candidates:
        content_elem = soup.select_one(selector)
        if content_elem:
            break

    return content_elem


def _preprocess_inline_sup_footnotes(
    content_elem,
    selector: str = "sup.ss-footnote",
    id_attrs: list[str] | tuple[str, ...] = ("footnote-id", "data-footnote-id"),
    text_attrs: list[str] | tuple[str, ...] = ("title", "data-footnote", "aria-label"),
    inline_expand: bool = True,
) -> dict[str, str]:
    """将内联脚注直接展开为括号说明。

    - 定位匹配 selector 的 <sup> 元素
    - 以 id_attrs/text_attrs 读取编号与文本
    - 用全角括号“（注：...）”替换原 <sup>，不保留 [^id]

    返回 {编号: 文本} 的映射，便于统计或后续处理。
    """
    if not content_elem:
        return {}

    try:
        sups = content_elem.select(selector)
        footnote_map: dict[str, str] = {}

        for sup in sups:
            fid = None
            for a in id_attrs:
                v = sup.get(a)
                if v and str(v).strip():
                    fid = str(v).strip()
                    break
            if not fid:
                txt = sup.get_text(strip=True)
                if txt:
                    fid = txt.strip()
            if not fid:
                continue

            fcontent = ""
            for a in text_attrs:
                v = sup.get(a)
                if v and str(v).strip():
                    fcontent = str(v).strip()
                    break

            if fcontent and fid not in footnote_map:
                footnote_map[fid] = fcontent

            try:
                if inline_expand and fcontent:
                    # 展开为括号说明，不保留 [^id]
                    sup.replace_with(NavigableString(f"（注：{fcontent}）"))
                else:
                    # 无有效内容时，移除脚注标记
                    sup.decompose()
            except Exception:
                pass

        if not footnote_map:
            return {}

        return footnote_map
    except Exception:
        return {}


def _strip_invisible_characters(content_elem):
    """移除内容中的不可见字符（如零宽空格），以避免转为Markdown后产生空行。

    说明：页面中常包含 U+200B/U+200C/U+200D 等零宽字符，以及 BOM 等不可见字符，
    这些字符在转Markdown时可能表现为额外的空段落。这里在 HTML 阶段统一清理。
    """
    # 扩展覆盖：零宽字符、BOM、Word Joiner、NBSP、段落/行分隔符
    invisible_chars_pattern = re.compile(
        r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u00a0\u2028\u2029]"
    )

    # 遍历所有文本节点并清理不可见字符
    for text_node in list(content_elem.find_all(string=True)):
        original_text = str(text_node)
        cleaned_text = invisible_chars_pattern.sub("", original_text)
        if cleaned_text != original_text:
            cleaned_text_stripped = cleaned_text.strip()
            if cleaned_text_stripped == "":
                # 如果清理后为空，则直接移除该文本节点，避免产生空行
                text_node.extract()
            else:
                text_node.replace_with(cleaned_text)


def _clean_and_normalize_sspai_content(content_elem) -> None:
    """清理和规范化少数派文章内容"""
    if not content_elem:
        return

    # 处理懒加载图片
    for img in content_elem.find_all("img", {"data-src": True}):
        img["src"] = img["data-src"]
        try:
            del img["data-src"]
        except Exception:
            pass

    for img in content_elem.find_all("img", {"data-original": True}):
        img["src"] = img["data-original"]
        try:
            del img["data-original"]
        except Exception:
            pass

    # 处理少数派特有的懒加载图片属性
    for img in content_elem.find_all("img", {"data-lazy-src": True}):
        img["src"] = img["data-lazy-src"]
        try:
            del img["data-lazy-src"]
        except Exception:
            pass

    # 移除脚本和样式
    for node in content_elem.find_all(["script", "style"]):
        try:
            node.decompose()
        except Exception:
            pass

    # 少数派特定的"减法策略"清单
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
        # 少数派特有的无关元素
        ".screen-reader-text",
        ".sr-only",
        ".skip-link",
        ".loading",
        ".spinner",
        ".placeholder",
        ".advertisement",
        ".ad",
        ".ads",
        ".advertisement-container",
        ".recommendation",
        ".recommended",
        ".related-articles",
        ".author-bio",
        ".author-info",
        ".post-author-info",
        ".post-actions",
        ".post-tools",
        ".post-utilities",
        ".entry-footer",
        ".post-footer",
        # 少数派特有的分享和互动元素
        ".share-post",
        ".like-post",
        ".bookmark-post",
        ".post-stats",
        ".view-count",
        ".like-count",
        # 二维码和扫码相关
        ".qr-code",
        ".qrcode",
        ".scan-code",
        # 订阅和关注相关
        ".subscribe",
        ".follow",
        ".follow-author",
    ]

    for selector in unwanted_in_content:
        for elem in content_elem.select(selector):
            try:
                elem.decompose()
            except Exception:
                pass

    # 移除包含特定推广链接的段落
    try:
        promo_hrefs = {
            "https://sspai.com/page/client",
            "https://sspai.com/mall",
            "https://sspai.com/link?target=https%3A%2F%2Fwww.xiaohongshu.com%2Fuser%2Fprofile%2F63f5d65d000000001001d8d4",
        }
        for href in promo_hrefs:
            for a in content_elem.select(f'a[href="{href}"]'):
                # 优先删除所在<p>，否则删除最近的块级父节点
                container = a.find_parent("p") or a.parent
                if container is None:
                    container = a
                try:
                    container.decompose()
                except Exception:
                    try:
                        container.extract()
                    except Exception:
                        pass
    except Exception:
        pass

    # 处理脚注：将内联脚注直接展开为括号说明
    _preprocess_inline_sup_footnotes(content_elem, inline_expand=True)

    # 移除不可见与零宽字符
    _strip_invisible_characters(content_elem)


def _process_sspai_content(
    html: str, url: str | None = None, title_hint: str | None = None
) -> FetchResult:
    """处理少数派文章内容"""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return FetchResult(title=None, html_markdown="")

    title, header_parts = _build_sspai_header_parts(soup, url, title_hint)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    content_elem = _build_sspai_content_element(soup)

    # 初始化md变量
    md = ""

    if content_elem:
        _clean_and_normalize_sspai_content(content_elem)
        from markdownall.core.html_to_md import html_fragment_to_markdown

        md = html_fragment_to_markdown(content_elem)
    else:
        md = ""

    md = header_str + md if header_str else md
    return FetchResult(title=title, html_markdown=md)


# 3. 抓取策略


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
    url: str, logger: Optional[ConvertLogger] = None, shared_browser: Any | None = None, should_stop: Optional[Callable[[], bool]] = None
) -> FetchResult:
    """策略2: 使用Playwright爬取原始HTML - 支持共享浏览器"""
    try:
        from playwright.sync_api import sync_playwright

        # 共享浏览器路径
        if shared_browser is not None and new_context_and_page is not None:
            context, page = new_context_and_page(shared_browser, apply_stealth=False)
            try:
                if should_stop and should_stop():
                    raise StopRequested()
                page.goto(url, wait_until="networkidle", timeout=30000)
                # 等待稳定（可停止）
                import time
                total_sleep = 2.0
                slept = 0.0
                while slept < total_sleep:
                    if should_stop and should_stop():
                        raise StopRequested()
                    step = min(0.2, total_sleep - slept)
                    time.sleep(step)
                    slept += step
                if read_page_content_and_title is not None:
                    if should_stop and should_stop():
                        raise StopRequested()
                    html, title = read_page_content_and_title(page, logger)
                else:
                    if should_stop and should_stop():
                        raise StopRequested()
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
            if should_stop and should_stop():
                raise StopRequested()
            page.goto(url, wait_until="networkidle", timeout=30000)
            # 等待稳定（可停止）
            import time
            total_sleep = 2.0
            slept = 0.0
            while slept < total_sleep:
                if should_stop and should_stop():
                    raise StopRequested()
                step = min(0.2, total_sleep - slept)
                time.sleep(step)
                slept += step
            if should_stop and should_stop():
                raise StopRequested()
            html, title = page.content(), page.title()
            browser.close()
            return FetchResult(title=title, html_markdown=html)

    except Exception as e:
        return FetchResult(
            title=None, html_markdown="", success=False, error=f"Playwright异常: {e}"
        )


# 4. 主入口函数


def fetch_sspai_article(
    session, url: str, logger: Optional[ConvertLogger] = None, shared_browser: Any | None = None, should_stop: Optional[Callable[[], bool]] = None
) -> FetchResult:
    """获取少数派文章内容（多策略爬取 + 统一内容处理）"""
    strategies = [
        lambda: _try_httpx_crawler(session, url),
        lambda: _try_playwright_crawler(url, logger, shared_browser, should_stop),
    ]

    max_retries = 2
    for i, strat in enumerate(strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    if logger:
                        logger.fetch_retry(f"少数派策略 {i}", retry, max_retries)
                    import time, random
                    total_sleep = random.uniform(2, 4)
                    slept = 0.0
                    while slept < total_sleep:
                        if should_stop and should_stop():
                            raise StopRequested()
                        step = min(0.2, total_sleep - slept)
                        time.sleep(step)
                        slept += step
                else:
                    if logger:
                        logger.fetch_start(f"少数派策略 {i}")

                if should_stop and should_stop():
                    raise StopRequested()
                r = strat()
                if r.success:
                    if logger:
                        logger.fetch_success()
                    # 统一处理：策略层只负责获取HTML，这里统一解析/清理/转换
                    if r.html_markdown:
                        if logger:
                            logger.parse_start()
                        if should_stop and should_stop():
                            raise StopRequested()
                        processed = _process_sspai_content(r.html_markdown, url, title_hint=r.title)

                        # 检查内容质量，如果内容太短，继续尝试下一个策略
                        content = processed.html_markdown or ""
                        if len(content) < 200:
                            if logger:
                                logger.parse_content_short(len(content))
                            break

                        if processed.title and logger:
                            logger.parse_title(processed.title)
                        if logger:
                            logger.clean_start()
                            logger.convert_start()
                            logger.convert_success()
                        return processed
                    else:
                        return r
                else:
                    if retry < max_retries - 1:
                        continue
                    else:
                        if logger:
                            logger.fetch_failed(f"少数派策略 {i}", r.error or "未知错误")
                        break
            except StopRequested:
                raise
            except Exception:
                if retry < max_retries - 1:
                    continue
                else:
                    if logger:
                        logger.fetch_failed(f"少数派策略 {i}", "异常")
                    break

        # 策略间等待
        if i < len(strategies):
            import time, random
            total_sleep = random.uniform(1, 2)
            slept = 0.0
            while slept < total_sleep:
                if should_stop and should_stop():
                    raise StopRequested()
                step = min(0.2, total_sleep - slept)
                time.sleep(step)
                slept += step

    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")
