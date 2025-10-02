"""
Next.js Blog 处理器 - 专门处理 Next.js 静态博客（如 guangzhengli.com/blog）
目标：保持完整 HTML 结构，删除 head、导航、目录、评论、页脚等非正文元素
示例页面： https://guangzhengli.com/blog/zh/vibe-coding-and-context-coding
"""

import random
import time
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup
from markitdown import MarkItDown

from markurldown.services.playwright_driver import (
    new_context_and_page,
    read_page_content_and_title,
    teardown_context_page,
)

# 1. 数据类


@dataclass
class FetchResult:
    """获取结果"""

    title: str | None
    html_markdown: str
    success: bool = True
    error: str | None = None


# 2. 底层工具函数（按调用关系排序）


def _extract_nextjs_title(soup: BeautifulSoup, title_hint: str | None = None) -> str | None:
    """提取Next.js博客文章标题"""
    title = None

    # 策略1: 优先查找主内容区域的标题
    title_selectors = [
        "main div.max-w-4xl div:first-child h1",  # 针对特定Next.js博客结构
        "article h1",
        ".post h1",
        ".blog-post h1",
        ".content h1",
        ".entry-content h1",
        "h1.post-title",
        "h1.entry-title",
        "h1.page-title",
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

    # 策略3: 最后的兜底方案，使用页面标题
    if not title:
        title_elem = soup.select_one("title")
        if title_elem:
            title = title_elem.get_text(strip=True)
            # 页面标题经常包含网站名称，需要清理
            if " - " in title:
                title = title.split(" - ")[0]

    return title


def _extract_nextjs_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    """提取Next.js博客文章的元数据（作者、发布时间等）"""
    metadata = {"author": None, "publish_time": None, "categories": None, "tags": None}

    # 提取作者信息
    author_selectors = [
        ".author",
        ".post-author",
        ".blog-author",
        ".entry-author",
        ".byline",
        ".author-name",
        "[data-author]",
        ".meta-author",
        ".post-meta .author",
    ]

    for selector in author_selectors:
        author_elem = soup.select_one(selector)
        if author_elem:
            # 尝试获取链接文本或直接文本
            author_link = author_elem.find("a")
            if author_link:
                metadata["author"] = author_link.get_text(strip=True)
            else:
                metadata["author"] = author_elem.get_text(strip=True)
            break

    # 提取发布时间
    time_selectors = [
        "main div.max-w-4xl div.my-4 p.text-sm",
        ".text-sm",
        "time[datetime]",
        ".publish-date",
        ".post-date",
        ".entry-date",
        ".blog-date",
        ".date",
        ".meta-date",
        ".post-meta .date",
        "[data-date]",
    ]

    for selector in time_selectors:
        time_elem = soup.select_one(selector)
        if time_elem:
            # 优先使用datetime属性
            datetime_attr = time_elem.get("datetime")
            if datetime_attr:
                metadata["publish_time"] = datetime_attr
            else:
                metadata["publish_time"] = time_elem.get_text(strip=True)
            break

    # 提取分类
    category_selectors = [
        ".categories a",
        ".post-categories a",
        ".blog-categories a",
        ".entry-categories a",
        ".category a",
        ".meta-category a",
        ".post-meta .category a",
        'a[rel="category"]',
    ]

    categories = []
    for selector in category_selectors:
        category_elems = soup.select(selector)
        for elem in category_elems:
            cat_text = elem.get_text(strip=True)
            if cat_text and cat_text not in categories:
                categories.append(cat_text)

    if categories:
        metadata["categories"] = ", ".join(categories)

    # 提取标签
    tag_selectors = [
        ".tags a",
        ".post-tags a",
        ".blog-tags a",
        ".entry-tags a",
        ".tag a",
        ".meta-tags a",
        ".post-meta .tags a",
        'a[rel="tag"]',
    ]

    tags = []
    for selector in tag_selectors:
        tag_elems = soup.select(selector)
        for elem in tag_elems:
            tag_text = elem.get_text(strip=True)
            if tag_text and tag_text not in tags:
                tags.append(tag_text)

    if tags:
        metadata["tags"] = ", ".join(tags)

    return metadata


# 3. 中层业务函数（按调用关系排序）


def _try_httpx_crawler(session, url: str) -> FetchResult:
    """策略1: 使用httpx爬取原始HTML"""
    try:
        import httpx

        # 使用与session相同的User-Agent
        headers = {
            "User-Agent": session.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        }

        # 如果session设置了no_proxy，则httpx也禁用代理
        client_kwargs = {"headers": headers}
        if hasattr(session, "trust_env") and not session.trust_env:
            client_kwargs["trust_env"] = False

        with httpx.Client(**client_kwargs) as client:
            response = client.get(url, timeout=30)
            response.raise_for_status()

            # 返回原始HTML，让上层进行两阶段处理
            return FetchResult(title=None, html_markdown=response.text)

    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"httpx异常: {e}")


def _try_playwright_crawler(url: str, shared_browser: Any | None = None) -> FetchResult:
    """策略2: 使用Playwright爬取原始HTML - 支持共享浏览器"""
    try:

        # 分支1：使用共享浏览器（为每个URL新建Context）
        if shared_browser is not None:
            context, page = new_context_and_page(shared_browser, apply_stealth=False)

            # 导航到页面
            page.goto(url, wait_until="networkidle", timeout=30000)

            # 等待页面稳定
            import time

            time.sleep(2)

            # 获取页面内容和标题
            html, title = read_page_content_and_title(page)

            # 清理资源
            teardown_context_page(context, page)

            # 返回原始HTML，让上层处理
            return FetchResult(title=title, html_markdown=html)

        # 分支2：使用独立浏览器（兜底方案）
        print("使用独立浏览器...")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--disable-plugins",
                ],
            )

            context, page = new_context_and_page(browser, apply_stealth=False)

            # 导航到页面
            page.goto(url, wait_until="networkidle", timeout=30000)

            # 等待页面稳定
            import time

            time.sleep(2)

            # 获取页面内容和标题
            html, title = read_page_content_and_title(page)

            # 返回原始HTML，让上层处理
            return FetchResult(title=title, html_markdown=html)

    except Exception as e:
        return FetchResult(
            title=None, html_markdown="", success=False, error=f"Playwright异常: {e}"
        )


def _build_nextjs_header_parts(
    soup: BeautifulSoup, url: str | None = None, title_hint: str | None = None
) -> tuple[str | None, list[str]]:
    """构建Next.js博客文章的Markdown头部信息片段（标题、来源、作者、时间等），并返回 (title, parts)"""
    header_parts: list[str] = []

    # 提取标题
    title = _extract_nextjs_title(soup, title_hint)
    if title:
        header_parts.append(f"# {title}")

    # 添加来源URL
    if url:
        header_parts.append(f"* 来源：{url}")

    # 提取并添加元数据
    metadata = _extract_nextjs_metadata(soup)

    # 将元数据合并为一行，借鉴weixin_handler的处理方式
    if metadata["author"] or metadata["publish_time"] or metadata["categories"] or metadata["tags"]:
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
            header_parts.append("* " + "  ".join(meta_parts))

    return title, header_parts


def _build_nextjs_content_element(soup: BeautifulSoup):
    """定位并返回Next.js博客正文容器元素"""
    content_elem = None

    # 策略1: 查找主内容区域
    content_selectors = [
        "div.max-w-4xl.mx-auto.w-full.px-6",
        "main",
        "main article",
        "main .post",
        "main .blog-post",
        "main .content",
        "main .entry-content",
        "article .post-content",
        "article .content",
        "article .entry-content",
        ".post .content",
        ".blog-post .content",
        ".entry-content",
        ".post-content",
        ".content",
    ]

    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            break

    # 策略2: 如果没找到，尝试查找包含h1的容器
    if not content_elem:
        h1_elem = soup.find("h1")
        if h1_elem:
            # 向上查找包含h1的内容容器
            for parent in h1_elem.parents:
                if parent.name in ["article", "main", "div"] and parent.get("class"):
                    content_elem = parent
                    break

    return content_elem


def _clean_and_normalize_nextjs_content(content_elem) -> None:
    """清洗与标准化Next.js博客正文容器"""
    if not content_elem:
        return

    # 懒加载图片与占位符处理
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

    # 移除脚本和样式
    for script in content_elem.find_all(["script", "style"]):
        try:
            script.decompose()
        except Exception:
            pass

    # 移除Next.js特定的非内容元素
    unwanted_in_content = [
        # 标题 和 meta
        "h1",
        "p.text-sm",
        # 导航和菜单
        "nav",
        ".nav",
        ".navigation",
        ".menu",
        ".navbar",
        "header",
        ".header",
        "#header",
        # 侧边栏和目录
        "aside",
        ".sidebar",
        ".toc",
        "#toc",
        ".table-of-contents",
        ".on-this-page",
        ".toc-container",
        ".toc-sidebar",
        ".hidden.text-sm.xl\\:block",
        ".hydrated",
        # 评论相关
        ".comments",
        "#comments",
        ".comment-list",
        ".comment-form",
        # 页脚
        "footer",
        ".footer",
        ".site-footer",
        # 社交分享
        ".social",
        ".social-links",
        ".share",
        ".share-buttons",
        ".social-media",
        ".social-share",
        # 面包屑
        ".breadcrumb",
        ".breadcrumbs",
        # 广告
        ".advertisement",
        ".ads",
        ".ad",
        ".ad-container",
        ".ad-banner",
        ".promo",
        ".sponsored",
        ".affiliate",
        # 相关文章推荐
        ".related-posts",
        ".more-posts",
        ".related",
        ".similar-posts",
        ".post-navigation",
        ".nav-links",
        ".page-links",
        # 作者信息（在正文中重复的）
        ".author-info",
        ".post-author",
        ".blog-author",
        # 元数据（在正文中重复的）
        ".post-meta",
        ".entry-meta",
        ".meta",
        ".meta-info",
        # 其他非内容元素
        ".screen-reader-text",
        ".sr-only",
        ".skip-link",
        ".loading",
        ".spinner",
        ".placeholder",
    ]

    for selector in unwanted_in_content:
        elements = content_elem.select(selector)
        for elem in elements:
            try:
                elem.decompose()
            except Exception:
                pass


def _process_nextjs_content(
    html: str, url: str | None = None, title_hint: str | None = None
) -> FetchResult:
    """处理Next.js内容，提取标题、元数据和过滤后的正文"""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 构建头部信息（包含标题抽取）
    title, header_parts = _build_nextjs_header_parts(soup, url, title_hint)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 正文：定位并构建正文容器
    content_elem = _build_nextjs_content_element(soup)

    # 清洗与标准化正文
    if content_elem:
        _clean_and_normalize_nextjs_content(content_elem)
        # 使用 html_fragment_to_markdown 转换正文内容
        from markurldown.core.html_to_md import html_fragment_to_markdown

        md = html_fragment_to_markdown(content_elem)

    # 最后拼接为全文
    if header_str:
        md = header_str + md if md else header_str

    try:
        return FetchResult(title=title, html_markdown=md)
    except Exception as e:
        print(f"创建FetchResult失败: {e}")
        return FetchResult(title=None, html_markdown="")


# 4. 主入口函数


def fetch_nextjs_article(session, url: str, shared_browser: Any | None = None) -> FetchResult:
    """
    获取Next.js博客文章内容

    使用多策略方案：
    1. 使用httpx获取原始HTML，然后统一进行内容过滤
    2. 使用Playwright获取原始HTML，然后统一进行内容过滤 (支持共享浏览器)
    """

    # 定义爬虫策略，按优先级排序
    crawler_strategies = [
        # 策略1: 使用httpx爬取原始HTML
        lambda: _try_httpx_crawler(session, url),
        # 策略2: 使用Playwright爬取原始HTML (支持共享浏览器)
        lambda: _try_playwright_crawler(url, shared_browser),
    ]

    # 尝试各种策略，增加重试机制
    max_retries = 2  # 每个策略最多重试2次

    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    print(f"[抓取] Next.js策略 {i} 重试 {retry}/{max_retries-1}...")
                    time.sleep(random.uniform(2, 4))  # 重试时等待
                else:
                    print(f"[抓取] Next.js策略 {i}...")

                result = strategy()
                if result.success:
                    print(f"[抓取] 成功获取内容")

                    # 两阶段处理：先获取原始HTML，再处理内容
                    if result.html_markdown:
                        print("[解析] 提取标题和正文...")
                        processed_result = _process_nextjs_content(
                            result.html_markdown, url, title_hint=result.title
                        )

                        # 检查内容质量，如果内容太短，继续尝试下一个策略
                        content = processed_result.html_markdown or ""
                        if len(content) < 200:
                            print(f"[解析] 内容太短 ({len(content)} 字符)，尝试下一个策略")
                            break

                        if processed_result.title:
                            print(f"[解析] 标题: {processed_result.title}")
                        print("[清理] 移除广告和无关内容...")
                        print("[转换] 转换为Markdown完成")
                        return processed_result
                    else:
                        return result
                else:
                    if retry < max_retries - 1:
                        continue
                    else:
                        print(f"[抓取] 策略 {i} 失败，尝试下一个策略")
                        break

            except Exception as e:
                if retry < max_retries - 1:
                    continue
                else:
                    print(f"[抓取] 策略 {i} 异常，尝试下一个策略")
                    break

        # 策略间等待
        if i < len(crawler_strategies):
            time.sleep(random.uniform(1, 2))

    # 所有策略都失败，返回空结果
    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")
