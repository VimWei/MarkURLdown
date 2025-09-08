"""
WordPress网站处理器 - 专门处理WordPress站点，如skywind.me
过滤掉导航、侧边栏、评论等非正文内容
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

def fetch_wordpress_article(session, url: str) -> FetchResult:
    """
    获取WordPress文章内容 - 专门针对skywind.me等WordPress站点优化

    使用多策略方案：
    1. 直接httpx + BeautifulSoup内容过滤
    2. Playwright + BeautifulSoup内容过滤
    """

    # 定义爬虫策略，按优先级排序
    crawler_strategies = [
        # 策略1: 直接httpx + 内容过滤
        lambda: _try_httpx_with_filtering(session, url),

        # 策略2: Playwright + 内容过滤
        lambda: _try_playwright_with_filtering(url),
    ]

    # 尝试各种策略，增加重试机制
    max_retries = 2  # 每个策略最多重试2次

    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    print(f"尝试WordPress获取策略 {i} (重试 {retry}/{max_retries-1})...")
                    time.sleep(random.uniform(2, 4))  # 重试时等待
                else:
                    print(f"尝试WordPress获取策略 {i}...")

                result = strategy()
                if result.success:
                    print(f"WordPress策略 {i} 成功!")
                    return result
                else:
                    print(f"WordPress策略 {i} 失败: {result.error}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print(f"WordPress策略 {i} 重试次数用尽，尝试下一个策略")
                        break

            except Exception as e:
                print(f"WordPress策略 {i} 异常: {e}")
                if retry < max_retries - 1:
                    continue
                else:
                    print(f"WordPress策略 {i} 重试次数用尽，尝试下一个策略")
                    break

        # 策略间等待
        if i < len(crawler_strategies):
            time.sleep(random.uniform(1, 2))

    # 所有策略都失败，返回空结果
    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")

def _try_httpx_with_filtering(session, url: str) -> FetchResult:
    """策略1: 直接httpx + BeautifulSoup内容过滤"""
    try:
        print("尝试httpx + 内容过滤...")
        import httpx

        # 使用与session相同的User-Agent
        headers = {
            "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        }

        # 如果session设置了no_proxy，则httpx也禁用代理
        client_kwargs = {"headers": headers}
        if hasattr(session, 'trust_env') and not session.trust_env:
            client_kwargs["trust_env"] = False

        with httpx.Client(**client_kwargs) as client:
            response = client.get(url, timeout=30)
            response.raise_for_status()

            # 使用BeautifulSoup解析并过滤内容
            return _process_wordpress_content(response.text, url)

    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"httpx异常: {e}")

def _try_playwright_with_filtering(url: str) -> FetchResult:
    """策略2: Playwright + BeautifulSoup内容过滤"""
    try:
        print("尝试Playwright + 内容过滤...")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 设置用户代理
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

            page.goto(url, wait_until='networkidle')
            time.sleep(2)  # 等待页面稳定

            # 获取页面内容
            html = page.content()
            title = page.title()
            browser.close()

        # 使用BeautifulSoup解析并过滤内容
        return _process_wordpress_content(html, url, title_hint=title)

    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"Playwright异常: {e}")

def _process_wordpress_content(html: str, url: str | None = None, title_hint: str | None = None) -> FetchResult:
    """处理WordPress内容，提取标题、元数据和过滤后的正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 查找标题 - 优先使用 Playwright 获取的标题
    title = None
    if title_hint:
        title = title_hint
        if " - " in title:
            title = title.split(" - ")[0]

    if not title:
        # 从HTML中提取标题
        title_selectors = [
            'h1.entry-title',
            'h1.post-title', 
            'h1.page-title',
            'h1',
            'title'
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                # 清理标题中的网站名称
                if ' - ' in title:
                    title = title.split(' - ')[0]
                break

    # 保持完整的HTML结构，只删除不需要的片段
    # 创建完整HTML的副本用于过滤（保持完整结构）
    html_copy = BeautifulSoup(html, 'lxml')
    print("保持完整HTML结构，只删除不需要的片段")

    # 定义需要移除的元素选择器 - 采用保守策略，只删除确定性的导航内容
    unwanted_selectors = [
        # 主要导航和菜单
        'nav', '.nav', '.navigation', '.menu', '.main-navigation', '.site-navigation',

        # 页面头部
        'head', '#header', '.header', '.site-header', '.page-header',

        # 侧边栏和组件
        '.sidebar', '.widget', '.widget-area', '.secondary', '.sidebar-widget',

        # 评论区域
        '.comments', '.comment', '#comments', '#respond', '.comment-form',
        '.comment-list', '.comment-reply', '.comment-respond',

        # 相关文章和推荐
        '.related-posts', '.more-posts', '.related', '.similar-posts',
        '.post-navigation', '.nav-links', '.page-links',

        # 社交分享
        '.social-share', '.share', '.social', '.social-links',
        '.share-buttons', '.social-media',

        # 面包屑导航
        '.breadcrumb', '.breadcrumbs', '.breadcrumb-trail',

        # 广告
        '.advertisement', '.ads', '.ad', '.ad-container', '.ad-banner',

        # 页脚
        '#footer', '.footer', '.site-footer',

        # 其他常见非内容元素
        '.skip-link', '.screen-reader-text', '.sr-only',

        # 相关阅读和推荐内容
        '.related-reading', '.related-posts', '.more-posts', '.related', '.similar-posts',

        # 特定于skywind.me的元素（根据分析结果）
        '#entry-author-info',
        '.pvc_stats.pvc_load_by_ajax_update',
        ".entry-utility",  ".likebtn_container",
        ".meta-prep.meta-prep-author", ".meta-sep", ".author.vcard"
    ]

    # 移除不需要的元素（从完整HTML中删除片段）
    removed_count = 0
    for selector in unwanted_selectors:
        elements = html_copy.select(selector)
        for elem in elements:
            elem.decompose()  # 完全移除元素
            removed_count += 1

    # 额外过滤：基于文本内容的智能过滤
    # 移除包含"相关阅读"、"相关文章"等关键词的段落
    related_keywords = ["相关阅读", "相关文章", "推荐阅读", "更多文章", "similar posts", "related posts"]
    
    for p in html_copy.find_all('p'):
        text = p.get_text(strip=True)
        if any(keyword in text for keyword in related_keywords):
            # 检查是否包含链接（通常是相关阅读的特征）
            if p.find('a'):
                p.decompose()
                removed_count += 1
                print(f"移除了相关阅读段落: {text[:50]}...")

    print(f"从完整HTML中移除了 {removed_count} 个非内容元素")

    # 使用MarkItDown转换过滤后的完整HTML
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
    """手动将HTML转换为Markdown，保留图片和链接"""

    # 处理图片
    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')
        if src:
            # 创建Markdown图片语法
            markdown_img = f"![{alt}]({src})"
            img.replace_with(markdown_img)

    # 处理链接
    for link in soup.find_all('a'):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if href and text:
            # 创建Markdown链接语法
            markdown_link = f"[{text}]({href})"
            link.replace_with(markdown_link)

    # 处理标题
    for i in range(1, 7):
        for heading in soup.find_all(f'h{i}'):
            text = heading.get_text(strip=True)
            if text:
                markdown_heading = f"{'#' * i} {text}"
                heading.replace_with(markdown_heading)

    # 处理代码块
    for pre in soup.find_all('pre'):
        code = pre.get_text()
        if code:
            markdown_code = f"```\n{code}\n```"
            pre.replace_with(markdown_code)

    # 处理内联代码
    for code in soup.find_all('code'):
        text = code.get_text()
        if text:
            markdown_inline_code = f"`{text}`"
            code.replace_with(markdown_inline_code)

    # 处理列表
    for ul in soup.find_all('ul'):
        items = []
        for li in ul.find_all('li'):
            text = li.get_text(strip=True)
            if text:
                items.append(f"- {text}")
        if items:
            markdown_list = '\n'.join(items)
            ul.replace_with(markdown_list)

    for ol in soup.find_all('ol'):
        items = []
        for i, li in enumerate(ol.find_all('li'), 1):
            text = li.get_text(strip=True)
            if text:
                items.append(f"{i}. {text}")
        if items:
            markdown_list = '\n'.join(items)
            ol.replace_with(markdown_list)

    # 处理段落
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(text + '\n\n')

    # 处理换行
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # 获取最终文本，保留空行
    text = soup.get_text(separator='\n')

    # 清理多余的空行，但保留必要的空行
    lines = []
    prev_empty = False
    for line in text.split('\n'):
        line_stripped = line.strip()
        if line_stripped:
            lines.append(line_stripped)
            prev_empty = False
        elif not prev_empty:
            lines.append('')
            prev_empty = True

    return '\n'.join(lines)
