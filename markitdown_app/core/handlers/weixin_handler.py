from __future__ import annotations

from dataclasses import dataclass
import time
import random

from bs4 import BeautifulSoup

from markitdown_app.core.html_to_md import html_fragment_to_markdown
from markitdown_app.core.common_utils import get_user_agents, extract_title_from_html
# 注意：crawlers模块已删除，使用内联实现


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


def fetch_weixin_article(session, url: str) -> FetchResult:
    """
    获取微信公众号文章内容 - 多策略尝试
    
    使用多种爬虫技术，按优先级尝试：
    1. Playwright - 现代化浏览器自动化（最可靠，能处理poc_token验证）
    2. httpx - 现代化HTTP客户端（备用策略）
    """
    
    # 定义爬虫策略，按优先级排序
    # 优先使用Playwright处理需要验证的链接，然后使用轻量级策略
    crawler_strategies = [
        # 策略1: Playwright - 最可靠，能处理微信的poc_token验证
        lambda: _try_playwright_crawler(url),
        
        # 策略2: httpx - 现代化HTTP客户端，备用策略
        lambda: _try_httpx_crawler(session, url),
    ]
    
    # 尝试各种策略，增加重试机制
    max_retries = 2  # 每个策略最多重试2次
    
    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    print(f"尝试微信获取策略 {i} (重试 {retry}/{max_retries-1})...")
                    time.sleep(random.uniform(3, 6))  # 重试时等待更长时间
                else:
                    print(f"尝试微信获取策略 {i}...")
                
                result = strategy()
                if result.success:
                    # 处理内容并检查质量
                    processed_result = _process_weixin_content(result.text_content, result.title, url)
                    
                    # 检查是否获取到验证页面
                    content = processed_result.html_markdown or ""
                    if content and ("环境异常" in content or "完成验证" in content or "去验证" in content):
                        print(f"策略 {i} 获取到验证页面，重试...")
                        if retry < max_retries - 1:
                            continue
                        else:
                            print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                            break
                    
                    # 检查标题是否包含验证信息
                    if processed_result.title and ("环境异常" in processed_result.title or "验证" in processed_result.title):
                        print(f"策略 {i} 标题包含验证信息，重试...")
                        if retry < max_retries - 1:
                            continue
                        else:
                            print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                            break
                    
                    print(f"策略 {i} 成功!")
                    return processed_result
                else:
                    print(f"策略 {i} 失败: {result.error}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        break
            except Exception as e:
                print(f"策略 {i} 异常: {e}")
                if retry < max_retries - 1:
                    continue
                else:
                    break
        
        # 策略间等待
        if i < len(crawler_strategies):
            time.sleep(random.uniform(2, 4))
    
    # 所有策略都失败，抛出异常让处理器回退到通用转换器
    raise Exception("所有微信获取策略都失败，回退到通用转换器")


def _try_playwright_crawler(url: str) -> CrawlerResult:
    """尝试使用 Playwright 爬虫 - 能处理微信的poc_token验证"""
    try:
        # 动态导入 Playwright
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # 启动浏览器，使用更多反检测参数
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
            
            # 创建上下文，模拟真实用户
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
            
            # 创建页面
            page = context.new_page()
            
            # 设置超时
            page.set_default_timeout(30000)
            
            # 访问页面
            print(f"Playwright: 正在访问 {url}")
            
            # 先访问微信首页建立会话
            try:
                print("Playwright: 正在访问微信首页建立会话...")
                page.goto("https://mp.weixin.qq.com/", wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(random.uniform(2000, 4000))
            except Exception as e:
                print(f"Playwright: 访问微信首页失败: {e}")
            
            # 访问目标页面
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            if not response or response.status >= 400:
                browser.close()
                return CrawlerResult(
                    success=False,
                    title=None,
                    text_content="",
                    error=f"HTTP {response.status if response else 'Unknown'}"
                )
            
            # 等待页面加载完成
            page.wait_for_timeout(random.uniform(3000, 6000))
            
            # 获取页面内容
            html = page.content()
            
            # 尝试获取标题
            title = None
            try:
                title = page.title()
            except:
                pass
            
            browser.close()
            
            return CrawlerResult(
                success=True,
                title=title,
                text_content=html
            )
            
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


def _try_httpx_crawler(session, url: str) -> CrawlerResult:
    """尝试使用 httpx 爬虫"""
    # 为微信设置特殊的请求头
    weixin_headers = _get_weixin_headers()
    
    try:
        import httpx
        # 创建新的httpx会话，使用微信专用请求头
        with httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers=weixin_headers
        ) as client:
            # 先访问微信首页建立会话
            try:
                print("httpx: 正在访问微信首页建立会话...")
                client.get("https://mp.weixin.qq.com/", timeout=15)
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"httpx: 访问微信首页失败: {e}")
            
            # 访问目标页面
            response = client.get(url, timeout=30)
            
            if response.status_code >= 400:
                return CrawlerResult(
                    success=False,
                    title=None,
                    text_content="",
                    error=f"HTTP {response.status_code}"
                )
            
            return CrawlerResult(
                success=True,
                title=extract_title_from_html(response.text),
                text_content=response.text
            )
    except ImportError:
        return CrawlerResult(
            success=False,
            title=None,
            text_content="",
            error="httpx not installed"
        )




def _get_weixin_headers() -> dict:
    """获取微信专用请求头"""
    return {
        "User-Agent": random.choice(get_user_agents()),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://mp.weixin.qq.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

def _process_weixin_content(html: str, title: str | None = None, url: str | None = None) -> FetchResult:
    """处理微信内容，提取标题、作者、发布日期和正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 查找标题 - 微信文章的标题选择器
    if not title:
        title_elem = (
            soup.find(attrs={'property': 'twitter:title'}) or
            soup.find(attrs={'property': 'og:title'}) or
            soup.find('h1', class_='rich_media_title') or
            soup.find('h1', id='activity-name') or
            soup.find('h1') or
            soup.find('title')
        )
        if title_elem:
            title = getattr(title_elem, 'get', lambda *_: None)('content') or title_elem.get_text(strip=True)

    # 查找公众号名称（之前错误地当作作者）
    account_name = None
    account_selectors = [
        'strong.rich_media_meta_nickname',
        'span.rich_media_meta_nickname', 
        'div.rich_media_meta_nickname',
        'a#js_name',
        'span#js_name',
        'div#js_name'
    ]
    
    for selector in account_selectors:
        elem = soup.select_one(selector)
        if elem:
            account_name = elem.get_text(strip=True)
            if account_name:
                break

    # 查找真正的作者信息
    author = None
    # 首先尝试从meta标签获取
    author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
    if author_meta:
        author = author_meta.get('content', '').strip()
    
    # 如果meta标签没有作者信息，尝试从文章内容中提取
    if not author:
        # 查找包含作者信息的文本模式
        content_elem = soup.find('div', class_='rich_media_content') or soup.find('div', id='js_content')
        if content_elem:
            # 查找包含"文/"、"作者："、"联系人："等关键词的文本
            author_patterns = [
                r'文/.*?：([^**\n]+)',
                r'作者[：:]\s*([^**\n]+)',
                r'联系人[：:]\s*([^**\n]+)',
                r'分析师[：:]\s*([^**\n]+)'
            ]
            
            import re
            content_text = content_elem.get_text()
            for pattern in author_patterns:
                match = re.search(pattern, content_text)
                if match:
                    author = match.group(1).strip()
                    # 清理作者名称，移除多余信息
                    author = re.sub(r'（.*?）', '', author)  # 移除括号内容
                    author = re.sub(r'微信.*', '', author)  # 移除微信信息
                    author = author.strip()
                    if author:
                        break

    # 查找发布日期
    publish_date = None
    date_selectors = [
        'em#publish_time',
        'span#publish_time',
        'div#publish_time',
        'em.rich_media_meta_text',
        'span.rich_media_meta_text',
        'div.rich_media_meta_text',
        'meta[property="article:published_time"]',
        'meta[name="publish_time"]'
    ]
    
    for selector in date_selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == 'meta':
                publish_date = elem.get('content', '').strip()
            else:
                publish_date = elem.get_text(strip=True)
            if publish_date:
                break

    # 查找内容区域 - 微信文章的内容选择器
    content_elem = soup.find('div', class_='rich_media_content') or soup.find('div', id='js_content')
    
    if content_elem:
        # 处理微信特有的图片懒加载
        for img in content_elem.find_all('img', {'data-src': True}):
            img['src'] = img['data-src']
            del img['data-src']
        
        # 处理微信的图片占位符
        for img in content_elem.find_all('img', {'data-original': True}):
            img['src'] = img['data-original']
            del img['data-original']
        
        # 移除脚本和样式
        for script in content_elem.find_all(['script', 'style']):
            script.decompose()
        
        # 移除微信特有的无用元素
        for elem in content_elem.find_all(['div'], class_=['qr_code_pc', 'qr_code_pc_inner']):
            elem.decompose()
        
        # 转换为markdown
        md = html_fragment_to_markdown(content_elem)
    else:
        md = ""

    # 构建完整的markdown内容，包含标题、URL、作者、发布日期
    header_parts = []
    
    # 添加标题
    if title:
        header_parts.append(f"# {title}")
    
    # 添加文章链接URL
    if url:
        header_parts.append(f"**文章链接：** {url}")
    
    # 添加作者、公众号名称和发布日期信息
    if author or account_name or publish_date:
        meta_info = []
        if author:
            meta_info.append(f"**作者：** {author}")
        if account_name:
            meta_info.append(f"**公众号：** {account_name}")
        if publish_date:
            meta_info.append(f"**发布时间：** {publish_date}")
        
        if meta_info:
            header_parts.append("\n".join(meta_info))
    
    # 如果有标题或元信息，添加到markdown开头
    if header_parts:
        header = "\n\n".join(header_parts) + "\n\n"
        md = header + md if md else header
    
    # 如果找到了内容但没有标题，尝试从页面其他地方获取
    elif not title and md:
        # 尝试从meta标签获取
        meta_title = soup.find('meta', {'property': 'og:title'})
        if meta_title:
            title = meta_title.get('content', '').strip()
        
        # 如果还是没有，尝试从页面标题获取
        if not title:
            page_title = soup.find('title')
            if page_title:
                title = page_title.get_text(strip=True)

        if title:
            md = (f"# {title}\n\n" + md) if md else f"# {title}\n\n"
    
    try:
        return FetchResult(title=title, html_markdown=md)
    except Exception as e:
        print(f"创建FetchResult失败: {e}")
        return FetchResult(title=None, html_markdown="")


