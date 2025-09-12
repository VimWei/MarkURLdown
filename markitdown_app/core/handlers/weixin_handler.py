from __future__ import annotations

from dataclasses import dataclass
import time
import random
from typing import Optional, Callable, Any

from bs4 import BeautifulSoup

from markitdown_app.core.html_to_md import html_fragment_to_markdown
from markitdown_app.services.playwright_driver import (
    new_context_and_page_from_shared,
    teardown_context_page,
    apply_stealth_and_defaults,
    establish_home_session,
    read_page_content_and_title,
)

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

def _try_playwright_crawler(url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> CrawlerResult:
    """尝试使用 Playwright 爬虫 - 能处理微信的poc_token验证"""
    try:
        # 若有共享 Browser，走共享路径：new_context → bootstrap → 访问 → 关闭 context
        if shared_browser is not None:
            context, page = new_context_and_page_from_shared(shared_browser, context_options={
                'extra_http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Referer': 'https://mp.weixin.qq.com/',
                }
            })
            try:
                try:
                    print("Playwright: 正在访问微信首页建立会话...")
                    if on_detail:
                        on_detail("正在访问微信首页建立会话...")
                    establish_home_session(page, "https://mp.weixin.qq.com/", None, on_detail)
                except Exception:
                    pass
                print(f"Playwright: 正在访问 {url}")
                if on_detail:
                    on_detail("正在访问目标文章...")
                response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
                if not response or response.status >= 400:
                    return CrawlerResult(success=False, title=None, text_content="", error=f"HTTP {response.status if response else 'Unknown'}")
                page.wait_for_timeout(random.uniform(3000, 6000))
                html, title = read_page_content_and_title(page, on_detail)
                return CrawlerResult(success=True, title=title, text_content=html)
            finally:
                teardown_context_page(context, page)
        # 否则走原始的 per-URL 浏览器路径
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
                    '--disable-images',  # 禁用图片加载以提高速度
                    '--disable-javascript',  # 禁用JavaScript，避免检测
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Referer': 'https://mp.weixin.qq.com/',
                }
            )
            page = context.new_page()
            apply_stealth_and_defaults(page)
            print(f"Playwright: 正在访问 {url}")
            if on_detail:
                on_detail("正在启动浏览器访问微信...")
            try:
                print("Playwright: 正在访问微信首页建立会话...")
                if on_detail:
                    on_detail("正在访问微信首页建立会话...")
                establish_home_session(page, "https://mp.weixin.qq.com/", None, on_detail)
            except Exception as e:
                print(f"Playwright: 访问微信首页失败: {e}")
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if on_detail:
                on_detail("正在访问目标文章...")
            if not response or response.status >= 400:
                browser.close()
                return CrawlerResult(success=False, title=None, text_content="", error=f"HTTP {response.status if response else 'Unknown'}")
            page.wait_for_timeout(random.uniform(3000, 6000))
            html, title = read_page_content_and_title(page, on_detail)
            browser.close()
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

def _build_weixin_header_parts(soup: BeautifulSoup, url: str | None, title_hint: str | None = None) -> tuple[str | None, list[str]]:
    """构建微信Markdown头部信息片段（标题、来源、作者、公众号、时间）。返回 (title, parts)。"""
    title = title_hint

    # 标题
    if not title:
        try:
            title_elem = soup.find('h1', class_='rich_media_title', id='activity-name')
            if title_elem:
                title = title_elem.get_text(strip=True)
        except Exception:
            pass

    # 作者
    author = None
    try:
        author_elem = soup.select_one('div#meta_content span.rich_media_meta.rich_media_meta_text')
        if author_elem:
            author = author_elem.get_text(strip=True)
    except Exception:
        pass

    # 公众号名称
    account_name = None
    try:
        account_elem = soup.select_one('span.rich_media_meta_nickname#profileBt a#js_name')
        if account_elem:
            account_name = account_elem.get_text(strip=True)
    except Exception:
        pass

    # 发布日期
    publish_date = None
    try:
        date_elem = soup.select_one('div#meta_content em#publish_time.rich_media_meta.rich_media_meta_text')
        if date_elem:
            publish_date = date_elem.get_text(strip=True)
    except Exception:
        pass

    # 地点
    location = None
    try:
        location_elem = soup.select_one('div#meta_content em#js_ip_wording_wrp span#js_ip_wording')
        if location_elem:
            location = location_elem.get_text(strip=True)
    except Exception:
        pass

    # 组装头部
    header_parts: list[str] = []
    if title:
        header_parts.append(f"# {title}")
    if url:
        header_parts.append(f"* 来源：{url}")
    if author or account_name or publish_date or location:
        meta_parts = []
        if author:
            meta_parts.append(f"{author}")
        if account_name:
            meta_parts.append(f"{account_name}")
        if publish_date:
            meta_parts.append(f"{publish_date}")
        if location:
            meta_parts.append(f"{location}")
        if meta_parts:
            header_parts.append("* " + "  ".join(meta_parts))

    return title, header_parts

def _build_weixin_content_element(soup: BeautifulSoup):
    """定位并返回微信正文容器元素。"""
    content_elem = (
        soup.find('div', class_='rich_media_content') or
        soup.find('div', id='js_content')
    )
    return content_elem

def _apply_style_removal_rules(root_elem, rules: list[dict]) -> None:
    """根据规则删除包含特定内联样式的标签"""
    try:
        for rule in rules:
            tag = rule.get('tag') if isinstance(rule, dict) else None
            styles = rule.get('styles') if isinstance(rule, dict) else None
            if not tag or not styles:
                continue
            nodes = list(root_elem.find_all(tag))
            nodes_to_remove = []
            for node in nodes:
                style_text = (node.get('style', '') or '').strip()
                if not style_text:
                    continue
                # AND：该行 styles 全部命中
                if all(sub in style_text for sub in styles):
                    nodes_to_remove.append(node)
            # 统一删除，避免边遍历边修改导致遗漏
            for node in nodes_to_remove:
                try:
                    node.decompose()
                except Exception:
                    pass
    except Exception:
        pass

def _clean_and_normalize_weixin_content(content_elem) -> None:
    """清洗与标准化微信正文容器（可持续完善规则）。"""
    # 懒加载图片与占位符
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

    # 移除无用元素（可扩展）
    for elem in content_elem.find_all(['div'], class_=['qr_code_pc', 'qr_code_pc_inner']):
        try:
            elem.decompose()
        except Exception:
            pass

    # 移除特定样式的标签
    # 一行一条规则，严格匹配，由 tag 和 styles 组成。
    # 同一条规则内，style 列表为 AND 关系。
    # 多条同 tag 规则，相当于 OR 关系。
    STYLE_REMOVAL_RULES: list[dict] = [
        {'tag': 'section', 'styles': ['border-width: 3px']},
        {'tag': 'section', 'styles': ['background-color: rgb(239, 239, 239)']},
    ]
    _apply_style_removal_rules(content_elem, STYLE_REMOVAL_RULES)

def _process_weixin_content(html: str, title: str | None = None, url: str | None = None) -> FetchResult:
    """处理微信内容，提取标题、作者、发布日期和正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 头部信息
    title, header_parts = _build_weixin_header_parts(soup, url, title)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 正文：定位并构建正文容器
    content_elem = _build_weixin_content_element(soup)

    # 清洗与标准化正文（规则可持续完善）
    if content_elem:
        _clean_and_normalize_weixin_content(content_elem)
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

def fetch_weixin_article(session, url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> FetchResult:
    """
    获取微信公众号文章内容 - 仅使用 Playwright

    采用 Playwright 浏览器自动化（可处理 poc_token 验证），并带重试。
    """

    max_retries = 2

    for retry in range(max_retries):
        try:
            if retry > 0:
                print(f"Playwright 策略重试 {retry}/{max_retries-1} ...")
                time.sleep(random.uniform(3, 6))
            else:
                print("尝试 Playwright 获取微信文章...")

            result = _try_playwright_crawler(url, on_detail, shared_browser)
            if result.success:
                if on_detail:
                    on_detail("微信内容获取成功，正在处理...")
                processed_result = _process_weixin_content(result.text_content, result.title, url)

                content = processed_result.html_markdown or ""
                if content and ("环境异常" in content or "完成验证" in content or "去验证" in content):
                    print("获取到验证页面，准备重试...")
                    if retry < max_retries - 1:
                        continue
                    break

                if processed_result.title and ("环境异常" in processed_result.title or "验证" in processed_result.title):
                    print("标题包含验证信息，准备重试...")
                    if retry < max_retries - 1:
                        continue
                    break

                print("Playwright 策略成功!")
                return processed_result
            else:
                print(f"Playwright 策略失败: {result.error}")
                if retry < max_retries - 1:
                    continue
                break
        except Exception as e:
            print(f"Playwright 策略异常: {e}")
            if retry < max_retries - 1:
                continue
            break

    raise Exception("微信内容获取失败，回退到通用转换器")
