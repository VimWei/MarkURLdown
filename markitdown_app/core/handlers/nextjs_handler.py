"""
Next.js Blog 处理器 - 专门处理 Next.js 静态博客（如 guangzhengli.com/blog）
目标：保持完整 HTML 结构，删除 head、导航、目录、评论、页脚等非正文元素
示例页面： https://guangzhengli.com/blog/zh/vibe-coding-and-context-coding
"""

import time
import random
from dataclasses import dataclass
from bs4 import BeautifulSoup
from markitdown import MarkItDown


@dataclass
class FetchResult:
    """获取结果"""
    title: str | None
    html_markdown: str
    success: bool = True
    error: str | None = None


def fetch_nextjs_article(session, url: str) -> FetchResult:
    """
    获取 Next.js 博客文章内容 - 针对常见 Next.js 博客主题优化

    多策略：
    1) httpx + BeautifulSoup 过滤
    2) Playwright + BeautifulSoup 过滤（备用）
    """

    crawler_strategies = [
        lambda: _try_httpx_with_filtering(session, url),
        lambda: _try_playwright_with_filtering(url),
    ]

    max_retries = 2

    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    print(f"尝试Next.js获取策略 {i} (重试 {retry}/{max_retries-1})...")
                    time.sleep(random.uniform(2, 4))
                else:
                    print(f"尝试Next.js获取策略 {i}...")

                result = strategy()
                if result.success:
                    print(f"Next.js策略 {i} 成功!")
                    return result
                else:
                    print(f"Next.js策略 {i} 失败: {result.error}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print("Next.js策略重试用尽，切换下一策略")
                        break
            except Exception as e:
                print(f"Next.js策略 {i} 异常: {e}")
                if retry < max_retries - 1:
                    continue
                else:
                    print("Next.js策略重试用尽，切换下一策略")
                    break

        if i < len(crawler_strategies):
            time.sleep(random.uniform(1, 2))

    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")


def _try_httpx_with_filtering(session, url: str) -> FetchResult:
    try:
        import httpx

        headers = {
            "User-Agent": session.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        }

        client_kwargs = {"headers": headers}
        if hasattr(session, "trust_env") and not session.trust_env:
            client_kwargs["trust_env"] = False

        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            return _process_nextjs_content(resp.text, url)
    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"httpx异常: {e}")


def _try_playwright_with_filtering(url: str) -> FetchResult:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                }
            )
            page.goto(url, wait_until="networkidle")
            time.sleep(2)
            html = page.content()
            title = page.title()
            browser.close()

        return _process_nextjs_content(html, url, title_hint=title)
    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"Playwright异常: {e}")


def _process_nextjs_content(html: str, url: str | None = None, title_hint: str | None = None) -> FetchResult:
    """保持完整HTML，仅删除确定性非内容元素；然后交给 MarkItDown。"""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    title = None
    if title_hint:
        title = title_hint
        if " - " in title:
            title = title.split(" - ")[0]

    if not title:
        for selector in ["h1", "title"]:
            node = soup.select_one(selector)
            if node:
                title = node.get_text(strip=True)
                if " - " in title:
                    title = title.split(" - ")[0]
                break

    html_copy = BeautifulSoup(html, "lxml")

    unwanted_selectors = [
        # 文档头
        "head",

        # 常见 Next.js 博客导航/侧栏/页脚/社交/文档目录
        "nav",
        ".nav",
        ".navigation",
        ".menu",
        "header",
        ".header",
        "#header",
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
        ".comments",
        "#comments",
        ".comment-list",
        ".comment-form",
        "footer",
        ".footer",
        ".site-footer",
        ".social",
        ".social-links",
        ".share",
        ".share-buttons",
        ".breadcrumb",
        ".breadcrumbs",
        ".advertisement",
        ".ads",
        ".ad",
        ".ad-container",
        ".ad-banner",
    ]

    removed = 0
    for selector in unwanted_selectors:
        for elem in html_copy.select(selector):
            elem.decompose()
            removed += 1

    try:
        md = MarkItDown()
        result = md.convert(str(html_copy))
        if result and getattr(result, "text_content", None):
            # 在标题下添加来源URL
            markdown_content = result.text_content
            if title and url:
                # 查找标题位置并插入来源行
                lines = markdown_content.split('\n')
                new_lines = []
                title_added = False
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    # 如果找到标题行且还没有添加来源行
                    if line.strip() == f"# {title}" and not title_added:
                        new_lines.append(f"来源：{url}")
                        title_added = True
                markdown_content = '\n'.join(new_lines)
            return FetchResult(title=title, html_markdown=markdown_content)
    except Exception as e:
        print(f"MarkItDown转换失败: {e}")

    # 兜底的简单手动转换（尽量保持简洁）
    markdown_content = _convert_html_to_markdown_manual(html_copy)
    if title and url:
        # 在标题下添加来源URL
        lines = markdown_content.split('\n')
        new_lines = []
        title_added = False
        for i, line in enumerate(lines):
            new_lines.append(line)
            # 如果找到标题行且还没有添加来源行
            if line.strip() == f"# {title}" and not title_added:
                new_lines.append(f"来源：{url}")
                title_added = True
        markdown_content = '\n'.join(new_lines)
    return FetchResult(title=title, html_markdown=markdown_content)


def _convert_html_to_markdown_manual(soup) -> str:
    # 图片
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src:
            img.replace_with(f"![{alt}]({src})")

    # 链接
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            a.replace_with(f"[{text}]({href})")

    # 标题
    for i in range(1, 7):
        for h in soup.find_all(f"h{i}"):
            t = h.get_text(strip=True)
            if t:
                h.replace_with(f"{'#' * i} {t}")

    # 代码块
    for pre in soup.find_all("pre"):
        code = pre.get_text()
        if code:
            pre.replace_with(f"```\n{code}\n```")

    # 段落与换行
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(text + "\n\n")

    text = soup.get_text(separator="\n")
    lines = []
    prev_empty = False
    for line in text.split("\n"):
        s = line.strip()
        if s:
            lines.append(s)
            prev_empty = False
        elif not prev_empty:
            lines.append("")
            prev_empty = True
    return "\n".join(lines)


