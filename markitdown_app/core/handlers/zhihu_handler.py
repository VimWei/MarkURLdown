from __future__ import annotations

from dataclasses import dataclass
import time
import random
from typing import Optional, Callable, Any

from bs4 import BeautifulSoup

from markitdown_app.core.html_to_md import html_fragment_to_markdown

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

def fetch_zhihu_article(session, url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> FetchResult:
    """
    获取知乎专栏文章内容
    使用 Playwright - 现代化浏览器自动化（最可靠，能处理知乎验证）
    """

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

                # 处理内容并检查质量
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
    print("💡 建议:")
    print("   1. 尝试使用VPN或代理")
    print("   2. 联系文章作者获取授权")
    print("   3. 使用其他工具手动复制内容")
    print("   4. 尝试在浏览器中直接访问文章")
    raise Exception("知乎文章爬取失败，请尝试其他方法")

def _try_playwright_crawler(url: str, on_detail: Optional[Callable[[str], None]] = None, shared_browser: Any | None = None) -> CrawlerResult:
    """尝试使用 Playwright 爬虫 - 能处理知乎的验证机制"""
    try:
        # 分支1：共享 Browser（为每个 URL 新建 Context）
        if shared_browser is not None:
            context = shared_browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                geolocation={'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                }
            )
            page = context.new_page()
            # 注入反检测脚本
            page.add_init_script("""
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 模拟真实的navigator属性
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });

                // 模拟真实的屏幕属性
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                });

                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                });

                // 模拟真实的时区
                Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                    value: function() {
                        return { timeZone: 'Asia/Shanghai' };
                    }
                });
            """)
            page.set_default_timeout(30000)

            # 首页 → 目标文章流程
            try:
                print("Playwright: 正在访问知乎首页建立会话...")
                if on_detail:
                    on_detail("正在访问知乎首页建立会话...")
                home_response = page.goto("https://www.zhihu.com/", wait_until='domcontentloaded', timeout=15000)
                if home_response and home_response.status == 200:
                    page.wait_for_timeout(random.uniform(2000, 4000))
                    try:
                        page.wait_for_timeout(random.uniform(500, 1500))
                        login_selectors = [
                            '.Modal-closeButton', '.SignFlow-close', '[aria-label="关闭"]',
                            '.Modal-close', '.close-button', 'button[aria-label="关闭"]'
                        ]
                        login_close = None
                        for selector in login_selectors:
                            login_close = page.query_selector(selector)
                            if login_close:
                                break
                        if login_close:
                            try:
                                login_close.click(timeout=3000)
                            except:
                                try:
                                    login_close.click(force=True, timeout=2000)
                                except:
                                    try:
                                        page.evaluate("arguments[0].click()", login_close)
                                    except:
                                        page.keyboard.press('Escape')
                            page.wait_for_timeout(500)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Playwright: 访问知乎首页失败: {e}")

            # 访问目标文章
            print("Playwright: 直接访问目标文章...")
            if on_detail:
                on_detail("正在访问目标文章...")
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待稳定与处理弹窗
            page.wait_for_timeout(random.uniform(1000, 2000))
            try:
                login_selectors = [
                    '.Modal-closeButton', '.SignFlow-close', '[aria-label="关闭"]', '.Modal-close',
                    '.close-button', 'button[aria-label="关闭"]', '.ant-modal-close', '.el-dialog__close'
                ]
                login_close = None
                for selector in login_selectors:
                    login_close = page.query_selector(selector)
                    if login_close:
                        break
                if login_close:
                    try:
                        login_close.click(timeout=5000)
                    except:
                        try:
                            login_close.click(force=True, timeout=3000)
                        except:
                            try:
                                page.evaluate("arguments[0].click()", login_close)
                            except:
                                try:
                                    page.keyboard.press('Escape')
                                except:
                                    pass
                    page.wait_for_timeout(1000)
            except Exception as e:
                try:
                    page.keyboard.press('Escape')
                except:
                    pass

            page.wait_for_timeout(random.uniform(1000, 2000))
            try:
                page.wait_for_selector('div.Post-RichTextContainer, div.Post-RichText, article, div.content', timeout=10000)
            except:
                pass

            if on_detail:
                on_detail("正在获取页面内容...")
            html = page.content()
            title = None
            try:
                title = page.title()
            except:
                pass

            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass

            return CrawlerResult(success=True, title=title, text_content=html)

        # 分支2：每 URL 独立 Browser（原路径）
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 启动真实的Chrome浏览器，使用成功的反检测配置
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

            # 创建上下文，模拟真实用户环境
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                geolocation={'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                }
            )

            # 创建页面
            page = context.new_page()

            # 注入反检测脚本
            page.add_init_script("""
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 模拟真实的navigator属性
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });

                // 模拟真实的屏幕属性
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                });

                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                });

                // 模拟真实的时区
                Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                    value: function() {
                        return { timeZone: 'Asia/Shanghai' };
                    }
                });
            """)

            # 设置超时
            page.set_default_timeout(30000)

            # 访问页面
            print(f"Playwright: 正在访问 {url}")
            if on_detail:
                on_detail("正在启动浏览器访问知乎...")

            # 优化的访问流程：首页 → 目标文章
            try:
                # 1. 先访问知乎首页建立会话
                print("Playwright: 正在访问知乎首页建立会话...")
                if on_detail:
                    on_detail("正在访问知乎首页建立会话...")
                home_response = page.goto("https://www.zhihu.com/", wait_until='domcontentloaded', timeout=15000)
                if home_response and home_response.status == 200:
                    print("Playwright: 知乎首页访问成功，获取cookies...")
                    # 模拟真实用户行为：等待页面加载
                    page.wait_for_timeout(random.uniform(2000, 4000))

                    # 模拟鼠标移动
                    page.mouse.move(random.randint(100, 800), random.randint(100, 400))
                    page.wait_for_timeout(random.uniform(500, 1500))

                    # 智能处理首页登录弹窗
                    try:
                        # 等待弹窗可能出现的时机
                        page.wait_for_timeout(random.uniform(500, 1500))

                        login_selectors = [
                            '.Modal-closeButton',
                            '.SignFlow-close',
                            '[aria-label="关闭"]',
                            '.Modal-close',
                            '.close-button',
                            'button[aria-label="关闭"]'
                        ]

                        login_close = None
                        for selector in login_selectors:
                            login_close = page.query_selector(selector)
                            if login_close:
                                break

                        if login_close:
                            print("Playwright: 发现首页登录弹窗，尝试关闭...")

                            # 多种关闭策略
                            try:
                                login_close.click(timeout=3000)
                                print("Playwright: 首页弹窗直接点击成功")
                            except:
                                try:
                                    login_close.click(force=True, timeout=2000)
                                    print("Playwright: 首页弹窗强制点击成功")
                                except:
                                    try:
                                        page.evaluate("arguments[0].click()", login_close)
                                        print("Playwright: 首页弹窗JavaScript点击成功")
                                    except:
                                        page.keyboard.press('Escape')
                                        print("Playwright: 首页弹窗使用ESC键关闭")

                            page.wait_for_timeout(500)
                        else:
                            print("Playwright: 首页未发现登录弹窗")
                    except Exception as e:
                        print(f"Playwright: 处理首页登录弹窗异常: {e}")
                else:
                    print("Playwright: 知乎首页访问失败")
            except Exception as e:
                print(f"Playwright: 访问知乎首页失败: {e}")

            # 2. 直接访问目标文章
            print("Playwright: 直接访问目标文章...")
            if on_detail:
                on_detail("正在访问目标文章...")
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 智能等待页面稳定并处理登录弹窗
            print("Playwright: 等待页面稳定并处理登录弹窗...")

            # 等待页面基本加载完成
            page.wait_for_timeout(random.uniform(1000, 2000))

            # 智能处理登录弹窗 - 多种策略
            try:
                # 查找各种可能的登录弹窗关闭按钮
                login_selectors = [
                    '.Modal-closeButton',
                    '.SignFlow-close',
                    '[aria-label="关闭"]',
                    '.Modal-close',
                    '.close-button',
                    'button[aria-label="关闭"]',
                    '.ant-modal-close',
                    '.el-dialog__close'
                ]

                login_close = None
                for selector in login_selectors:
                    login_close = page.query_selector(selector)
                    if login_close:
                        break

                if login_close:
                    print("Playwright: 发现登录弹窗，尝试关闭...")

                    # 策略1: 直接点击
                    try:
                        login_close.click(timeout=5000)
                        print("Playwright: 直接点击成功")
                    except:
                        # 策略2: 强制点击
                        try:
                            login_close.click(force=True, timeout=3000)
                            print("Playwright: 强制点击成功")
                        except:
                            # 策略3: 使用JavaScript点击
                            try:
                                page.evaluate("arguments[0].click()", login_close)
                                print("Playwright: JavaScript点击成功")
                            except:
                                # 策略4: 按ESC键关闭弹窗
                                try:
                                    page.keyboard.press('Escape')
                                    print("Playwright: 使用ESC键关闭弹窗")
                                except:
                                    print("Playwright: 所有关闭策略都失败，继续执行...")

                    # 短暂等待确认弹窗关闭
                    page.wait_for_timeout(1000)
                else:
                    print("Playwright: 未发现登录弹窗")

            except Exception as e:
                print(f"Playwright: 处理登录弹窗异常: {e}")
                # 尝试按ESC键作为备用方案
                try:
                    page.keyboard.press('Escape')
                    print("Playwright: 使用ESC键作为备用方案")
                except:
                    pass

            # 最终等待页面完全稳定
            page.wait_for_timeout(random.uniform(1000, 2000))

            # 检查页面标题而不是响应状态，因为知乎可能返回200但内容是403页面
            try:
                page_title = page.title()
                print(f"Playwright: 获取到标题: {page_title}")
                if "403" in page_title or "Forbidden" in page_title:
                    browser.close()
                    return CrawlerResult(
                        success=False,
                        title=None,
                        text_content="",
                        error=f"Page title indicates 403: {page_title}"
                    )
            except Exception as e:
                print(f"Playwright: 获取标题失败: {e}")
                # 继续执行，可能页面正在加载

            # 模拟真实用户阅读行为
            page.wait_for_timeout(random.uniform(3000, 6000))

            # 模拟鼠标移动和滚动
            page.mouse.move(random.randint(300, 700), random.randint(300, 600))
            page.wait_for_timeout(random.uniform(500, 1500))
            page.mouse.wheel(0, random.randint(100, 400))
            page.wait_for_timeout(random.uniform(1000, 2000))

            # 尝试等待特定元素加载
            try:
                # 等待内容区域加载
                page.wait_for_selector('div.Post-RichTextContainer, div.Post-RichText, article, div.content', timeout=10000)
                print("Playwright: 找到内容区域")
            except:
                print("Playwright: 未找到内容区域，但继续获取页面内容...")

            # 获取页面内容
            if on_detail:
                on_detail("正在获取页面内容...")
            html = page.content()

            # 尝试获取标题
            title = None
            try:
                title = page.title()
                print(f"Playwright: 获取到标题: {title}")
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

def _process_zhihu_content(html: str, title: str | None = None, url: str | None = None) -> FetchResult:
    """处理知乎内容，提取标题、作者、发布日期和正文"""
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 查找标题 - 知乎专栏的标题选择器
    if not title:
        title_elem = (
            soup.find('h1', class_='Post-Title') or
            soup.find('h1', class_='ArticleItem-title') or
            soup.find('h1', class_='Post-Title') or
            soup.find(attrs={'property': 'og:title'}) or
            soup.find(attrs={'property': 'twitter:title'}) or
            soup.find('h1') or
            soup.find('title')
        )
        if title_elem:
            title = getattr(title_elem, 'get', lambda *_: None)('content') or title_elem.get_text(strip=True)

    # 查找作者信息
    author = None
    # 首先尝试从meta标签获取
    author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
    if author_meta:
        author = author_meta.get('content', '').strip()

    # 其次尝试从作者信息容器中提取（知乎页面常见：div.AuthorInfo-content）
    if not author:
        author_info = soup.select_one('div.AuthorInfo-content')
        if author_info:
            # 优先取带有作者名字的可见文本
            # 常见结构含 a.AuthorInfo-name 或 span 等
            name_elem = author_info.select_one('.AuthorInfo-name, a, span')
            if name_elem:
                candidate = name_elem.get_text(strip=True)
                if candidate:
                    author = candidate
            if not author:
                text = author_info.get_text(" ", strip=True)
                if text:
                    author = text

    # 如果上述方式没有作者信息，尝试从文章内容中提取
    if not author:
        # 查找包含作者信息的文本模式
        content_elem = soup.find('div', class_='Post-RichTextContainer') or soup.find('div', class_='Post-RichText')
        if content_elem:
            # 查找包含"作者："、"文/"等关键词的文本
            author_patterns = [
                r'作者[：:]\s*([^**\n]+)',
                r'文/.*?：([^**\n]+)',
                r'编辑[：:]\s*([^**\n]+)',
                r'来源[：:]\s*([^**\n]+)'
            ]

            import re
            content_text = content_elem.get_text()
            for pattern in author_patterns:
                match = re.search(pattern, content_text)
                if match:
                    author = match.group(1).strip()
                    # 清理作者名称，移除多余信息
                    author = re.sub(r'（.*?）', '', author)
                    author = re.sub(r'知乎.*', '', author)
                    author = author.strip()
                    if author:
                        break

    # 查找发布日期
    publish_date = None
    date_selectors = [
        'time[datetime]',
        'div.ContentItem-time',
        'span[data-tooltip]',
        'div.Post-Header .ContentItem-time',
        'meta[property="article:published_time"]',
        'meta[name="publish_time"]'
    ]

    for selector in date_selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == 'meta':
                publish_date = elem.get('content', '').strip()
            elif elem.get('datetime'):
                publish_date = elem.get('datetime', '').strip()
            else:
                # ContentItem-time 常位于包含相对时间/tooltip 的容器
                # 获取尽量干净的可见文本
                publish_date = elem.get_text(strip=True)
            if publish_date:
                break

    # 查找内容区域 - 知乎专栏的内容选择器
    content_elem = None
    content_selectors = [
        'div.Post-RichTextContainer',
        'div[data-zop-feedtype]',
        'div.Post-RichText',
        'div.ArticleItem-content',
        'div.entry-content',
        'article',
        'div.content'
    ]

    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            break

    if content_elem:
        # 处理知乎特有的图片懒加载
        for img in content_elem.find_all('img', {'data-src': True}):
            img['src'] = img['data-src']
            del img['data-src']

        # 处理知乎的图片占位符
        for img in content_elem.find_all('img', {'data-original': True}):
            img['src'] = img['data-original']
            del img['data-original']

        # 移除脚本和样式
        for script in content_elem.find_all(['script', 'style']):
            script.decompose()

        # 移除知乎特有的无用元素
        for elem in content_elem.find_all(['div'], class_=['Post-RichTextContainer']):
            # 保留主要内容，移除广告等
            pass

        # 移除知乎的推荐内容
        for elem in content_elem.find_all(['div'], class_=['Recommendation-Main', 'Card', 'Card--padding']):
            elem.decompose()

        # 清理知乎直答链接 - 保留文本，移除链接
        _clean_zhihu_zhida_links(content_elem)

        # 清理知乎外部链接重定向 - 恢复原始链接
        _clean_zhihu_external_links(content_elem)

        # 注意：图片格式检测已移至图片下载阶段处理，以提升内容处理速度

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
        header_parts.append(f"**来源：** {url}")

    # 添加作者和发布日期信息
    if author or publish_date:
        meta_info = []
        if author:
            meta_info.append(f"**作者：** {author}")
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
