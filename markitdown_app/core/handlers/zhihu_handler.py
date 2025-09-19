from __future__ import annotations

from dataclasses import dataclass
import time
import random
from typing import Optional, Callable, Any

import re
from bs4 import NavigableString
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from markitdown_app.core.html_to_md import html_fragment_to_markdown
from markitdown_app.core.handlers import generic_handler as _generic
from markitdown_app.services.playwright_driver import (
    new_context_and_page,
    teardown_context_page,
    try_close_modal_with_selectors,
    read_page_content_and_title,
    wait_for_selector_stable,
)

# 1. 数据类
@dataclass
class CrawlerResult:
    """爬虫结果"""
    success: bool
    title: str | None
    text_content: str
    error: str | None = None

@dataclass
class FetchResult:
    title: str | None
    html_markdown: str

@dataclass
class ZhihuPageType:
    """知乎页面类型判定结果"""
    is_answer_page: bool
    is_column_page: bool
    kind: str  # "answer" | "column" | "unknown"

# 选择器与等待点常量（集中管理，便于维护与复用）
ZHIHU_SELECTORS = {
    'home_login_close': [
        '.Modal-closeButton',
        '.SignFlow-close',
        '[aria-label="关闭"]',
        '.Modal-close',
        '.close-button',
        'button[aria-label="关闭"]',
    ],
    'login_close': [
        '.Modal-closeButton',
        '.SignFlow-close',
        '[aria-label="关闭"]',
        '.Modal-close',
        '.close-button',
        'button[aria-label="关闭"]',
        '.ant-modal-close',
        '.el-dialog__close',
        '.Qrcode-close',
    ],
    'modal_detection': [
        '.Modal-backdrop',
        '.Qrcode-qrcode',
    ],
    'expand_buttons': [
        'button.ContentItem-expandButton',
        'button:has-text("展开阅读全文")',
        'text="展开阅读全文"',
        'a:has-text("展开阅读全文")',
        'span:has-text("展开阅读全文")',
        '[data-za-detail-view-element_name="展开阅读全文"]',
        '.RichContent-inner button',
        '.RichContent-inner a',
        'button[data-za-detail-view-element_name="展开阅读全文"]',
    ],
}

WAIT_SELECTOR_BY_TYPE = {
    'answer': 'h1.QuestionHeader-title, div.QuestionAnswer-content',
    'column': 'article',
    'unknown': 'main',
}

# 2. 底层工具函数（按调用关系排序）
def _detect_zhihu_page_type(url: str | None) -> ZhihuPageType:
    """根据 URL 判定知乎页面类型（URL-only）。

    - URL 规则：
      - 专栏：zhuanlan.zhihu.com/p/{id}
      - 回答：www.zhihu.com/question/{qid}/answer/{aid}
    """
    is_answer = False
    is_column = False

    try:
        if url:
            parsed = urlparse(url)
            hostname = (parsed.hostname or '').lower()
            path = parsed.path or ''

            if hostname == 'zhuanlan.zhihu.com' and path.startswith('/p/'):
                is_column = True
            elif hostname in {'www.zhihu.com', 'zhihu.com'} and '/answer/' in path:
                parts = [p for p in path.split('/') if p]
                if len(parts) >= 4 and parts[0] == 'question' and parts[2] == 'answer':
                    is_answer = True

    except Exception:
        pass

    kind = 'answer' if is_answer else ('column' if is_column else 'unknown')
    return ZhihuPageType(is_answer_page=is_answer, is_column_page=is_column, kind=kind)

def _extract_zhihu_title(soup: BeautifulSoup, page_type: ZhihuPageType) -> str | None:
    """统一的知乎标题提取逻辑。
    优先按页面类型的专用选择器提取，其次通用回退：h1 -> og:title -> <title>。
    未来新增页面类型时，只需在这里扩展策略。
    """
    title: str | None = None

    try:
        # 页面类型策略优先
        if page_type.is_answer_page and not title:
            node = soup.find('h1', class_='QuestionHeader-title')
            if node:
                title = node.get_text(strip=True)
                print(f"从回答页h1获取标题: {title}")
            else:
                node = soup.find('h1')
                if node:
                    title = node.get_text(strip=True)
                    print(f"从回答页备用h1获取标题: {title}")

        elif page_type.is_column_page and not title:
            node = soup.find('h1', class_='Post-Title')
            if node:
                title = node.get_text(strip=True)
                print(f"从专栏h1获取标题: {title}")
            else:
                meta_node = soup.find('meta', attrs={'property': 'og:title'})
                if meta_node:
                    content_val = meta_node.get('content', '')
                    if content_val:
                        title = content_val.strip()
                        print(f"从专栏<meta og:title>获取标题: {title}")

        # 通用回退
        if not title:
            node = soup.find('h1')
            if node:
                title = node.get_text(strip=True)
                print(f"从通用h1获取标题: {title}")

        if not title:
            meta_node = soup.find('meta', attrs={'property': 'og:title'})
            if meta_node:
                content_val = meta_node.get('content', '')
                if content_val:
                    title = content_val.strip()
                    print(f"从<meta og:title>获取标题: {title}")

        if not title:
            node = soup.find('title')
            if node:
                title = node.get_text(strip=True)
                print(f"从<head><title>获取标题: {title}")
    except Exception as e:
        print(f"标题提取异常: {e}")

    return title

def _extract_zhihu_author(soup: BeautifulSoup, page_type: ZhihuPageType) -> tuple[str | None, str | None, str | None]:
    """提取作者信息，返回 (作者名, 作者主页URL, 作者徽章)。

    - 回答页：优先从 `div.ContentItem-meta a.UserLink-link` 或 `AuthorInfo-name a` 获取
    - 专栏页：优先从 `a.AuthorInfo-name`, `span.AuthorInfo-name a`, 或 meta[name="author"] 获取
    - URL 归一化：将 // 或 / 开头的链接标准化为绝对地址
    """
    name: str | None = None
    href: str | None = None
    badge: str | None = None

    try:
        if page_type.is_answer_page:
            # 尝试多个选择器，找到有文本内容的作者链接
            link_selectors = [
                'div.ContentItem-meta a.UserLink-link',
                'div.ContentItem-meta span.UserLink.AuthorInfo-name a',
                'a.UserLink-link'
            ]

            link = None
            for selector in link_selectors:
                links = soup.select(selector)
                # 找到第一个有文本内容的链接
                for candidate_link in links:
                    candidate_name = candidate_link.get_text(strip=True)
                    if candidate_name:  # 确保有文本内容
                        link = candidate_link
                        break
                if link:
                    break

            if link:
                name = link.get_text(strip=True) or None
                href = link.get('href') or None
            badge_node = soup.select_one('div.ContentItem-meta .AuthorInfo-detail .AuthorInfo-badgeText')
            if badge_node:
                badge_text = badge_node.get_text(strip=True)
                badge = badge_text or badge

        elif page_type.is_column_page:
            link = soup.select_one('a.AuthorInfo-name')
            if not link:
                link = soup.select_one('span.AuthorInfo-name a')
            if not link:
                link = soup.select_one('div.Post-Author a')
            if link:
                name = link.get_text(strip=True) or None
                href = link.get('href') or None
            if not name:
                meta_author = soup.find('meta', attrs={'name': 'author'})
                if meta_author:
                    content_val = meta_author.get('content', '').strip()
                    name = content_val or name
            badge_node = soup.select_one('div.Post-Author .AuthorInfo-detail .AuthorInfo-badgeText')
            if badge_node:
                badge_text = badge_node.get_text(strip=True)
                badge = badge_text or badge

        # 归一化链接
        if href:
            try:
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://www.zhihu.com' + href
            except Exception:
                pass
    except Exception:
        pass

    return name, href, badge

def _extract_zhihu_time(soup: BeautifulSoup, page_type: ZhihuPageType) -> str | None:
    """提取发布时间（可能包含地点，纯文本）。
    """
    text: str | None = None
    try:
        if page_type.is_answer_page:
            node = soup.select_one('div.ContentItem-time')
            if node:
                # 该节点文本可能包含地点，例如："编辑于 2023-07-13 23:39 ・江苏"
                text = node.get_text(" ", strip=True) or None
            if not text:
                node = soup.select_one('div.RichContent div.ContentItem-time')
                if node:
                    text = node.get_text(" ", strip=True) or None

        elif page_type.is_column_page:
            # 优先从专栏正文附近的时间/地点块获取
            node = soup.select_one('div.ContentItem-time')
            if node:
                # 该节点文本通常形如："发布于 2025-08-17 23:29・江苏"
                text = node.get_text(" ", strip=True) or None
            if not text:
                meta_time = soup.find('meta', attrs={'property': 'article:published_time'})
                if meta_time:
                    content_val = meta_time.get('content', '').strip()
                    if content_val:
                        text = content_val

    except Exception:
        pass

    if text:
        text = " ".join(text.split())
    return text or None

def _normalize_zhihu_links(content_elem):
    """将知乎站内链接标准化为绝对URL，修复 // 或 / 开头的链接。"""
    for a in content_elem.find_all('a'):
        href = a.get('href')
        if not href:
            continue
        try:
            if href.startswith('//'):
                a['href'] = 'https:' + href
            elif href.startswith('/'):
                a['href'] = 'https://www.zhihu.com' + href
        except Exception:
            # 忽略个别异常，继续处理其他链接
            continue

def _strip_invisible_characters(content_elem):
    """移除内容中的不可见字符（如零宽空格），以避免转为Markdown后产生空行。

    说明：知乎页面中常包含 U+200B/U+200C/U+200D 等零宽字符，以及 BOM 等不可见字符，
    这些字符在转Markdown时可能表现为额外的空段落。这里在 HTML 阶段统一清理。
    """

    # 扩展覆盖：零宽字符、BOM、Word Joiner、NBSP、段落/行分隔符
    invisible_chars_pattern = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u00a0\u2028\u2029]")

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

def _clean_zhihu_zhida_links(content_elem):
    """清理知乎直答链接，保留文本内容，移除链接"""
    import re
    from bs4 import NavigableString

    # 查找所有包含知乎直答链接的<a>标签
    zhida_links = content_elem.find_all('a', href=re.compile(r'https://zhida\.zhihu\.com/search\?'))

    for link in zhida_links:
        # 获取链接文本
        link_text = link.get_text(strip=True)

        # 如果链接文本不为空，用纯文本替换链接
        if link_text:
            # 创建纯文本节点
            text_node = NavigableString(link_text)
            # 用纯文本替换链接
            link.replace_with(text_node)
        else:
            # 如果链接文本为空，直接移除
            link.decompose()

    # 额外处理：清理可能存在的其他知乎内部链接
    internal_links = content_elem.find_all('a', href=re.compile(r'https://www\.zhihu\.com/(question|answer|p)/'))

    for link in internal_links:
        link_text = link.get_text(strip=True)
        if link_text:
            text_node = NavigableString(link_text)
            link.replace_with(text_node)
        else:
            link.decompose()

def _clean_zhihu_external_links(content_elem):
    """清理知乎外部链接重定向，恢复原始链接"""
    import re
    from urllib.parse import unquote, urlparse, parse_qs
    from bs4 import NavigableString

    # 查找所有包含知乎重定向链接的<a>标签
    redirect_links = content_elem.find_all('a', href=re.compile(r'https://link\.zhihu\.com/\?target='))

    for link in redirect_links:
        href = link.get('href', '')

        try:
            # 解析URL参数
            parsed_url = urlparse(href)
            query_params = parse_qs(parsed_url.query)

            # 获取target参数
            if 'target' in query_params and query_params['target']:
                target_url = query_params['target'][0]
                # URL解码
                decoded_url = unquote(target_url)

                # 更新链接的href属性
                link['href'] = decoded_url
                print(f"Playwright: 恢复外部链接: {href} -> {decoded_url}")
            else:
                # 如果target参数为空或不存在，将链接转换为纯文本
                link_text = link.get_text(strip=True)
                if link_text:
                    text_node = NavigableString(link_text)
                    link.replace_with(text_node)
                    print(f"Playwright: 转换无效重定向链接为纯文本: {href}")
                else:
                    link.decompose()
                    print(f"Playwright: 移除空的重定向链接: {href}")

        except Exception as e:
            print(f"Playwright: 处理重定向链接异常: {e}")
            # 异常情况下也转换为纯文本
            link_text = link.get_text(strip=True)
            if link_text:
                text_node = NavigableString(link_text)
                link.replace_with(text_node)
            else:
                link.decompose()
            continue

# 3. 中层业务函数（按调用关系排序）
def _apply_zhihu_stealth_and_defaults(page: Any, default_timeout_ms: int = 30000) -> None:
    """Apply Zhihu-specific stealth scripts and set default timeouts.

    Zhihu requires more comprehensive stealth scripts.
    """
    try:
        page.add_init_script(
            """
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // Realistic navigator props
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            // Screen size
            Object.defineProperty(screen, 'width', { get: () => 1920 });
            Object.defineProperty(screen, 'height', { get: () => 1080 });
            // Timezone
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() { return { timeZone: 'Asia/Shanghai' }; }
            });
            // 知乎特定的反检测
            Object.defineProperty(navigator, 'permissions', { get: () => ({ query: () => Promise.resolve({ state: 'granted' }) }) });
            """
        )
    except Exception:
        pass
    try:
        page.set_default_timeout(default_timeout_ms)
    except Exception:
        pass

def _get_wait_selector_for_page_type(page_type: ZhihuPageType) -> str:
    """根据页面类型返回等待用选择器。"""
    if page_type.is_answer_page:
        return WAIT_SELECTOR_BY_TYPE['answer']
    if page_type.is_column_page:
        return WAIT_SELECTOR_BY_TYPE['column']
    return WAIT_SELECTOR_BY_TYPE['unknown']

def _try_click_expand_buttons(page) -> bool:
    """尝试点击知乎的“展开阅读全文”相关按钮，返回是否有点击发生。"""
    expand_selectors = ZHIHU_SELECTORS['expand_buttons']
    try:
        for selector in expand_selectors:
            try:
                expand_buttons = page.query_selector_all(selector)
                if expand_buttons:
                    print(f"Playwright: 找到展开按钮 ({selector}): {len(expand_buttons)}个")
                    for button in expand_buttons:
                        try:
                            if not hasattr(button, 'is_visible') or button.is_visible():
                                button.scroll_into_view_if_needed()
                                page.wait_for_timeout(500)
                                button.click(timeout=3000)
                                print("Playwright: 成功点击展开按钮")
                                page.wait_for_timeout(3000)
                                return True
                        except Exception as e:
                            print(f"Playwright: 点击展开按钮失败: {e}")
                            continue
                else:
                    print(f"Playwright: 未找到展开按钮 ({selector})")
            except Exception as e:
                print(f"Playwright: 查找展开按钮失败 ({selector}): {e}")
                continue
    except Exception:
        pass
    return False

def _goto_target_and_prepare_content(page, url: str, on_detail: Optional[Callable[[str], None]] = None) -> None:
    """访问目标URL，处理登录弹窗，等待页面稳定，并尝试展开全文。"""
    # 访问目标
    try:
        if on_detail:
            try:
                on_detail("正在访问目标URL...")
            except Exception:
                pass
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
    except Exception:
        pass

    # 初步等待
    page.wait_for_timeout(random.uniform(2000, 3000))

    # 关闭登录弹窗
    try:
        print("Playwright: 检查并关闭登录弹窗...")
        
        # 使用增强的弹窗关闭函数，包含重试机制和特定弹窗检测
        modal_closed = try_close_modal_with_selectors(
            page, 
            ZHIHU_SELECTORS['login_close'],
            max_attempts=3,
            modal_detection_selectors=ZHIHU_SELECTORS['modal_detection'],
            use_escape_fallback=True
        )

        if not modal_closed:
            print("Playwright: 无法完全关闭登录弹窗")
    except Exception as e:
        print(f"Playwright: 处理登录弹窗时出错: {e}")

    # 等待页面稳定
    page.wait_for_timeout(random.uniform(1000, 2000))

    # 处理知乎回答页面的展开逻辑
    try:
        print("Playwright: 开始查找展开按钮...")
        
        # 点击展开按钮
        _try_click_expand_buttons(page)
    except Exception as e:
        print(f"Playwright: 处理展开按钮时出错: {e}")

    # 最后等待关键内容选择器
    try:
        page_type = _detect_zhihu_page_type(url)
        key = 'answer' if page_type.is_answer_page else ('column' if page_type.is_column_page else 'unknown')
        wait_for_selector_stable(page, WAIT_SELECTOR_BY_TYPE, page_type_key=key, timeout_ms=10000)
    except Exception:
        wait_for_selector_stable(page, WAIT_SELECTOR_BY_TYPE, page_type_key='unknown', timeout_ms=10000)

def _try_playwright_crawler(url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> CrawlerResult:
    """尝试使用 Playwright 爬虫 - 能处理知乎的验证机制"""
    # 检测页面类型
    page_type = _detect_zhihu_page_type(url)

    try:
        # 分支1：共享 Browser（为每个 URL 新建 Context）
        if shared_browser is not None:
            context, page = new_context_and_page(shared_browser, apply_stealth=False)
            # 应用知乎特定的反检测脚本
            _apply_zhihu_stealth_and_defaults(page)

            # 访问目标URL
            _goto_target_and_prepare_content(page, url, on_detail)
            html, title = read_page_content_and_title(page, on_detail)
            teardown_context_page(context, page)
            return CrawlerResult(success=True, title=title, text_content=html)

        # 分支2：每 URL 独立 Browser（原路径）
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 启动Chrome浏览器，使用必要的反检测配置
            browser = p.chromium.launch(
                headless=False,  # 使用非headless模式以绕过检测
                channel="chrome",  # 使用系统安装的Chrome
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                ]
            )

            # 创建独立的上下文和页面
            context, page = new_context_and_page(browser, apply_stealth=False)
            # 应用知乎特定的反检测脚本
            _apply_zhihu_stealth_and_defaults(page)

            # 访问目标URL
            _goto_target_and_prepare_content(page, url, on_detail)
            html, title = read_page_content_and_title(page, on_detail)

            return CrawlerResult(success=True, title=title, text_content=html)

    except ImportError:
        return CrawlerResult(
            success=False,
            title=None,
            text_content="",
            error="Playwright not installed. Install with: pip install playwright && playwright install"
        )
    except Exception as e:
        return CrawlerResult(
            success=False,
            title=None,
            text_content="",
            error=f"Playwright error: {str(e)}"
        )

def _build_zhihu_header_parts(soup: BeautifulSoup, url: str | None) -> tuple[str | None, list[str]]:
    """构建Markdown头部信息片段（标题、来源、作者、时间），并返回 (title, parts)。"""
    # 检测页面类型
    page_type = _detect_zhihu_page_type(url)

    header_parts: list[str] = []
    title: str | None = _extract_zhihu_title(soup, page_type)
    if title:
        header_parts.append(f"# {title}")

    if url:
        header_parts.append(f"* 来源：{url}")

    author_name, author_url, author_badge = _extract_zhihu_author(soup, page_type)
    if author_name:
        if author_url:
            if author_badge:
                header_parts.append(f"* 作者：[{author_name}]({author_url})  {author_badge}")
            else:
                header_parts.append(f"* 作者：[{author_name}]({author_url})")
        else:
            if author_badge:
                header_parts.append(f"* 作者：{author_name}  {author_badge}")
            else:
                header_parts.append(f"* 作者：{author_name}")

    publish_time = _extract_zhihu_time(soup, page_type)
    if publish_time:
        header_parts.append(f"* 时间：{publish_time}")

    return title, header_parts

def _build_zhihu_content_element(soup: BeautifulSoup, page_type: ZhihuPageType):
    """定位并组装知乎页面的内容容器，返回用于转 Markdown 的根元素。
    - 专栏页：优先 `div.Post-RichTextContainer`，回退若干候选
    - 回答页：优先 `RichContent-inner`，回退若干候选
    - 未知页：使用保守选择器回退
    """
    content_elem = None
    if page_type.is_answer_page:
        # 回答页：直接使用 RichContent-inner 作为正文容器
        content_elem = soup.select_one('div.RichContent-inner')
        if not content_elem:
            # 回退：从 RichContent 容器内再取一次
            rich_container = soup.select_one('div.RichContent.RichContent--unescapable')
            if rich_container:
                content_elem = rich_container.select_one('div.RichContent-inner')

    elif page_type.is_column_page:
        # 专栏页：严格使用 Post-RichTextContainer 作为正文容器
        content_elem = soup.select_one('div.Post-RichTextContainer')

    else:
        # 未知类型：不做猜测，保持 None
        content_elem = None

    return content_elem

def _clean_and_normalize_zhihu_content(content_elem, page_type: ZhihuPageType, soup: BeautifulSoup | None = None) -> None:
    """清洗知乎内容容器，标准化图片与链接，移除噪音元素。"""
    # 图片懒加载与占位符
    for img in content_elem.find_all('img', {'data-src': True}):
        img['src'] = img['data-src']
        del img['data-src']
    for img in content_elem.find_all('img', {'data-original': True}):
        img['src'] = img['data-original']
        del img['data-original']

    # 移除脚本和样式
    for script in content_elem.find_all(['script', 'style']):
        script.decompose()

    # 移除广告元素
    for elem in content_elem.find_all(['div'], class_=['RichText-ADLinkCardContainer']):
        elem.decompose()

    # 链接处理与标准化
    _clean_zhihu_zhida_links(content_elem)
    _clean_zhihu_external_links(content_elem)
    _normalize_zhihu_links(content_elem)

    # 移除不可见与零宽字符
    _strip_invisible_characters(content_elem)

def _process_zhihu_content(html: str, title_hint: str | None = None, url: str | None = None) -> FetchResult:
    """处理知乎内容，拼接头部信息(标题、作者、发布日期)和正文，并返回 markdown 内容"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 检测页面类型
    page_type = _detect_zhihu_page_type(url)

    # 先构建头部信息（包含标题抽取）
    title, header_parts = _build_zhihu_header_parts(soup, url)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 再查找和构建正文区域
    content_elem = _build_zhihu_content_element(soup, page_type)
    # 清洗与标准化正文区域
    if content_elem:
        _clean_and_normalize_zhihu_content(content_elem, page_type, soup)
        md = html_fragment_to_markdown(content_elem)
    else:
        md = ""

    # 最后拼接为全文
    if header_str:
        md = header_str + md if md else header_str

    try:
        return FetchResult(title=title, html_markdown=md)
    except Exception as e:
        print(f"创建FetchResult失败: {e}")
        return FetchResult(title=None, html_markdown="")

# 4. 主入口函数
def fetch_zhihu_article(session, url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> FetchResult:
    """
    使用 Playwright 获取知乎页面内容 - 现代化浏览器自动化（最可靠，能处理知乎验证）
    """
    # 检测页面类型
    page_type = _detect_zhihu_page_type(url)

    # 若页面类型未知，委托给通用处理器
    if page_type.kind == 'unknown':
        try:
            # 先轻量策略，再增强，再直接httpx
            for strat in (
                lambda: _generic._try_lightweight_markitdown(url, session),
                lambda: _generic._try_enhanced_markitdown(url, session),
                lambda: _generic._try_direct_httpx(url, session),
            ):
                r = strat()
                if r.success and r.text_content:
                    return FetchResult(title=r.title, html_markdown=r.text_content)
        except Exception:
            pass

    # 使用Playwright爬虫处理知乎文章
    max_retries = 2  # 最多重试2次

    for retry in range(max_retries):
        try:
            if retry > 0:
                print(f"尝试知乎获取 (重试 {retry}/{max_retries-1})...")
                time.sleep(random.uniform(3, 6))  # 重试时等待更长时间
            else:
                print("尝试知乎获取...")

            result = _try_playwright_crawler(url, on_detail, shared_browser)
            if result.success:
                # 显示内容获取成功状态
                if on_detail:
                    on_detail("知乎内容获取成功，正在处理...")

                # 处理内容并检查质量（将 Playwright 的标题作为提示，不作为最终值）
                processed_result = _process_zhihu_content(result.text_content, result.title, url)

                # 检查是否获取到验证页面 - 更精确的检测
                content = processed_result.html_markdown or ""
                if content and len(content) > 1000:  # 如果内容足够长，说明不是验证页面
                    print("成功获取到内容!")
                    return processed_result
                elif content and ("验证" in content or "登录" in content or "访问被拒绝" in content or "403" in content or "404" in content):
                    print("获取到验证页面，重试...")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print("重试次数用尽")
                        break

                # 检查标题是否包含验证信息
                if processed_result.title and ("验证" in processed_result.title or "登录" in processed_result.title or "访问被拒绝" in processed_result.title):
                    print("标题包含验证信息，重试...")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print("重试次数用尽")
                        break

                print("成功!")
                return processed_result
            else:
                print(f"获取失败: {result.error}")
                if retry < max_retries - 1:
                    continue
                else:
                    break
        except Exception as e:
            print(f"获取异常: {e}")
            if retry < max_retries - 1:
                continue
            else:
                break

    # 所有策略都失败，提供详细的错误信息和用户指导
    print("⚠️  知乎文章爬取遇到限制")
    raise Exception("知乎文章爬取失败，请尝试其他方法")
