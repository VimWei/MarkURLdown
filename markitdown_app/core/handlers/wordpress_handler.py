"""
WordPress网站处理器 - 专门处理WordPress站点，如skywind.me
过滤掉导航、侧边栏、评论等非正文内容
"""

import time
import random
from dataclasses import dataclass
from typing import Any
from bs4 import BeautifulSoup
from markitdown import MarkItDown

from markitdown_app.services.playwright_driver import (
    new_context_and_page,
    teardown_context_page,
    read_page_content_and_title
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

def _extract_wordpress_title(soup: BeautifulSoup, title_hint: str | None = None) -> str | None:
    """提取WordPress文章标题"""
    title = None

    # 策略1: 优先查找 <div id="content" role="main"> 下的标题
    title_selectors = [
        'div#content[role="main"] h1.entry-title',
        'div#content[role="main"] h1.post-title',
        'div#content[role="main"] h1.page-title',
        'div#content[role="main"] h1',
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
        title_elem = soup.select_one('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # 页面标题经常包含网站名称，需要清理
            if ' - ' in title:
                title = title.split(' - ')[0]

    return title

def _extract_wordpress_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    """提取WordPress文章的元数据（作者、发布时间等）"""
    metadata = {
        'author': None,
        'publish_time': None,
        'categories': None,
        'tags': None
    }

    # 提取作者信息
    author_selectors = [
        '.author.vcard a',
        '.entry-author a',
        '.post-author a',
        '.byline a',
        '.author-name a',
        '.author a'
    ]

    for selector in author_selectors:
        author_elem = soup.select_one(selector)
        if author_elem:
            metadata['author'] = author_elem.get_text(strip=True)
            break

    # 提取发布时间
    time_selectors = [
        'time.entry-date',
        '.entry-date',
        '.post-date',
        '.published',
        'time[datetime]',
        '.date'
    ]

    for selector in time_selectors:
        time_elem = soup.select_one(selector)
        if time_elem:
            # 优先使用datetime属性
            datetime_attr = time_elem.get('datetime')
            if datetime_attr:
                metadata['publish_time'] = datetime_attr
            else:
                metadata['publish_time'] = time_elem.get_text(strip=True)
            break

    # 提取分类
    category_selectors = [
        '.entry-categories a',
        '.post-categories a',
        '.categories a',
        '.cat-links a',
        'a[rel="category tag"]',  # 匹配 rel="category tag" 的链接
        '.entry-utility a[rel="category tag"]'  # 在 entry-utility 容器内匹配
    ]

    categories = []
    for selector in category_selectors:
        category_elems = soup.select(selector)
        for elem in category_elems:
            cat_text = elem.get_text(strip=True)
            if cat_text and cat_text not in categories:
                categories.append(cat_text)

    if categories:
        metadata['categories'] = ', '.join(categories)

    # 提取标签
    tag_selectors = [
        '.entry-tags a',
        '.post-tags a',
        '.tags a',
        '.tag-links a',
        'a[rel="tag"]',  # 匹配 rel="tag" 的链接
        '.entry-utility a[rel="tag"]'  # 在 entry-utility 容器内匹配
    ]

    tags = []
    for selector in tag_selectors:
        tag_elems = soup.select(selector)
        for elem in tag_elems:
            tag_text = elem.get_text(strip=True)
            if tag_text and tag_text not in tags:
                tags.append(tag_text)

    if tags:
        metadata['tags'] = ', '.join(tags)

    return metadata


# 3. 中层业务函数（按调用关系排序）

def _try_httpx_crawler(session, url: str) -> FetchResult:
    """策略1: 使用httpx爬取原始HTML"""
    try:
        print("尝试httpx 爬取原始HTML...")
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

            # 返回原始HTML，让上层统一处理
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
            page.goto(url, wait_until='networkidle', timeout=30000)

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
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-extensions',
                    '--disable-plugins',
                ]
            )

            context, page = new_context_and_page(browser, apply_stealth=False)

            # 导航到页面
            page.goto(url, wait_until='networkidle', timeout=30000)

            # 等待页面稳定
            import time
            time.sleep(2)

            # 获取页面内容和标题
            html, title = read_page_content_and_title(page)

            # 返回原始HTML，让上层处理
            return FetchResult(title=title, html_markdown=html)

    except Exception as e:
        return FetchResult(title=None, html_markdown="", success=False, error=f"Playwright异常: {e}")

def _build_wordpress_header_parts(soup: BeautifulSoup, url: str | None = None, title_hint: str | None = None) -> tuple[str | None, list[str]]:
    """构建WordPress文章的Markdown头部信息片段（标题、来源、作者、时间等），并返回 (title, parts)"""
    header_parts: list[str] = []

    # 提取标题
    title = _extract_wordpress_title(soup, title_hint)
    if title:
        header_parts.append(f"# {title}")

    # 添加来源URL
    if url:
        header_parts.append(f"* 来源：{url}")

    # 提取并添加元数据
    metadata = _extract_wordpress_metadata(soup)

    # 将元数据合并为一行，借鉴weixin_handler的处理方式
    if metadata['author'] or metadata['publish_time'] or metadata['categories'] or metadata['tags']:
        meta_parts = []
        if metadata['author']:
            meta_parts.append(f"{metadata['author']}")
        if metadata['publish_time']:
            meta_parts.append(f"{metadata['publish_time']}")
        if metadata['categories']:
            meta_parts.append(f"{metadata['categories']}")
        if metadata['tags']:
            meta_parts.append(f"{metadata['tags']}")
        if meta_parts:
            header_parts.append("* " + "  ".join(meta_parts))

    return title, header_parts

def _build_wordpress_content_element(soup: BeautifulSoup):
    """定位并返回WordPress正文容器元素"""
    content_elem = None

    # 策略1: 查找 <div id="content" role="main"> 下的 <div class="entry-content">
    content_main = soup.find('div', id='content', role='main')
    if content_main:
        content_elem = content_main.find('div', class_='entry-content')

    # 策略2: 直接查找 <div class="entry-content">
    if not content_elem:
        content_elem = soup.find('div', class_='entry-content')

    # 策略3: 查找其他常见的WordPress内容容器
    if not content_elem:
        content_selectors = [
            'div.post-content',
            'div.entry-body',
            'div.article-content',
            'div.content',
            'article .entry-content',
            'main .entry-content',
            '.post .entry-content'
        ]

        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

    return content_elem

def _clean_and_normalize_wordpress_content(content_elem) -> None:
    """清洗与标准化WordPress正文容器"""
    if not content_elem:
        return

    # 懒加载图片与占位符处理
    for img in content_elem.find_all('img', {'data-src': True}):
        img['src'] = img['data-src']
        try:
            del img['data-src']
        except Exception:
            pass

    for img in content_elem.find_all('img', {'data-original': True}):
        img['src'] = img['data-original']
        try:
            del img['data-original']
        except Exception:
            pass

    # 移除脚本和样式
    for script in content_elem.find_all(['script', 'style']):
        try:
            script.decompose()
        except Exception:
            pass

    # 移除WordPress特定的非内容元素
    unwanted_in_content = [
        # 广告和推广
        '.advertisement', '.ads', '.ad', '.ad-container', '.ad-banner',
        '.promo', '.sponsored', '.affiliate',

        # 社交分享按钮
        '.social-share', '.share', '.social', '.social-links',
        '.share-buttons', '.social-media',

        # 相关文章推荐
        '.related-posts', '.more-posts', '.related', '.similar-posts',
        '.post-navigation', '.nav-links', '.page-links',

        # 评论相关
        '.comments', '.comment', '#comments', '#respond', '.comment-form',
        '.comment-list', '.comment-reply', '.comment-respond',

        # 作者信息（在正文中重复的）
        '.entry-author-info', '.author-info', '.post-author',

        # 元数据（在正文中重复的）
        '.entry-meta', '.post-meta', '.entry-utility',

        # 其他非内容元素
        '.wp-caption-text', '.gallery-caption',
        '.screen-reader-text', '.sr-only',
        '.skip-link',

        # 特定于skywind.me的元素（根据分析结果）
        '#entry-author-info',
        '.pvc_stats.pvc_load_by_ajax_update',
        ".entry-utility",  ".likebtn_container",
        ".meta-prep.meta-prep-author", ".meta-sep", ".author.vcard"
    ]

    for selector in unwanted_in_content:
        elements = content_elem.select(selector)
        for elem in elements:
            try:
                elem.decompose()
            except Exception:
                pass

def _process_wordpress_content(html: str, url: str | None = None, title_hint: str | None = None) -> FetchResult:
    """处理WordPress内容，提取标题、元数据和过滤后的正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 构建头部信息（包含标题抽取）
    title, header_parts = _build_wordpress_header_parts(soup, url, title_hint)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 正文：定位并构建正文容器
    content_elem = _build_wordpress_content_element(soup)

    # 初始化md变量
    md = ""

    # 清洗与标准化正文
    if content_elem:
        _clean_and_normalize_wordpress_content(content_elem)
        # 使用 html_fragment_to_markdown 转换正文内容
        from markitdown_app.core.html_to_md import html_fragment_to_markdown
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

def fetch_wordpress_article(session, url: str, shared_browser: Any | None = None) -> FetchResult:
    """
    获取WordPress文章内容

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
                    print(f"[抓取] WordPress策略 {i} 重试 {retry}/{max_retries-1}...")
                    time.sleep(random.uniform(2, 4))  # 重试时等待
                else:
                    print(f"[抓取] WordPress策略 {i}...")

                result = strategy()
                if result.success:
                    print(f"[抓取] 成功获取内容")

                    # 两阶段处理：先获取原始HTML，再处理内容
                    if result.html_markdown:
                        print("[解析] 提取标题和正文...")
                        processed_result = _process_wordpress_content(result.html_markdown, url, title_hint=result.title)
                        
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
