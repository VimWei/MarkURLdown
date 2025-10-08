from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from bs4 import BeautifulSoup

from markdownall.app_types import ConvertLogger
from markdownall.core.exceptions import StopRequested
from markdownall.core.html_to_md import html_fragment_to_markdown
from markdownall.services.playwright_driver import (
    new_context_and_page,
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


def _goto_target_and_prepare_content(
    page,
    url: str,
    logger: Optional[ConvertLogger] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> None:
    """访问目标URL并准备内容 - 微信版本"""
    if logger:
        logger.info("正在访问微信文章...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass  # 微信机制：即使URL错误也会返回错误页面，真正的异常检测在内容层面

    # sleep with stop checks (break into slices)
    total_wait = random.uniform(3000, 6000) / 1000.0
    slept = 0.0
    while slept < total_wait:
        if should_stop and should_stop():
            raise StopRequested()
        step = min(0.2, total_wait - slept)
        page.wait_for_timeout(int(step * 1000))
        slept += step


def _try_playwright_crawler(
    url: str,
    logger: Optional[ConvertLogger] = None,
    shared_browser: Any | None = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> CrawlerResult:
    """尝试使用 Playwright 爬虫 - 能处理微信的poc_token验证"""
    try:
        # 无论是否共享，都强制使用独立浏览器实例
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
                    "--disable-images",  # 禁用图片加载以提高速度
                    "--disable-javascript",  # 禁用JavaScript，避免检测
                ],
            )

            # 创建独立的上下文和页面
            context, page = new_context_and_page(browser, apply_stealth=False)

            # 访问目标URL并准备内容
            if should_stop and should_stop():
                raise StopRequested()
            _goto_target_and_prepare_content(page, url, logger, should_stop)

            # 使用 playwright_driver 的 read_page_content_and_title
            if should_stop and should_stop():
                raise StopRequested()
            html, title = read_page_content_and_title(page, logger)

            return CrawlerResult(success=True, title=title, text_content=html)

    except ImportError:
        return CrawlerResult(
            success=False,
            title=None,
            text_content="",
            error="Playwright not installed. Install with: pip install playwright && playwright install",
        )
    except Exception as e:
        return CrawlerResult(
            success=False, title=None, text_content="", error=f"Playwright error: {str(e)}"
        )


def _build_weixin_header_parts(
    soup: BeautifulSoup, url: str | None, title_hint: str | None = None
) -> tuple[str | None, str | None, list[str]]:
    """构建微信Markdown头部信息片段（标题、来源、作者、公众号、时间）。返回 (title, account_name, header_parts)"""
    title = title_hint

    # 标题
    if not title:
        try:
            title_elem = soup.find("h1", class_="rich_media_title", id="activity-name")
            if title_elem:
                title = title_elem.get_text(strip=True)
        except Exception:
            pass

    # 作者
    author = None
    try:
        author_elem = soup.select_one("div#meta_content span.rich_media_meta.rich_media_meta_text")
        if author_elem:
            author = author_elem.get_text(strip=True)
    except Exception:
        pass

    # 公众号名称
    account_name = None
    try:
        account_elem = soup.select_one("span.rich_media_meta_nickname#profileBt a#js_name")
        if account_elem:
            account_name = account_elem.get_text(strip=True)
    except Exception:
        pass

    # 发布日期
    publish_date = None
    try:
        date_elem = soup.select_one(
            "div#meta_content em#publish_time.rich_media_meta.rich_media_meta_text"
        )
        if date_elem:
            publish_date = date_elem.get_text(strip=True)
    except Exception:
        pass

    # 地点
    location = None
    try:
        location_elem = soup.select_one("div#meta_content em#js_ip_wording_wrp span#js_ip_wording")
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

    return title, account_name, header_parts


def _build_weixin_content_element(soup: BeautifulSoup):
    """定位并返回微信正文容器元素。"""
    content_elem = soup.find("div", class_="rich_media_content") or soup.find(
        "div", id="js_content"
    )
    return content_elem


def _apply_removal_rules(root_elem, rules: list[dict]) -> None:
    """
    根据规则删除元素

    支持的规则类型：
    1. style 规则：根据内联样式过滤
    2. class 规则：根据 CSS 类名过滤
    3. id 规则：根据元素 ID 过滤
    """
    try:
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            tag = rule.get("tag")
            if not tag:
                continue

            nodes = list(root_elem.find_all(tag))
            nodes_to_remove = []

            for node in nodes:
                should_remove = True  # 默认应该删除，需要所有条件都满足

                # 处理 style 规则
                styles = rule.get("styles")
                if styles:
                    style_text = (node.get("style", "") or "").strip()
                    # styles 列表内为 AND 关系（必须全部匹配）
                    if not style_text or not all(sub in style_text for sub in styles):
                        should_remove = False

                # 处理 class 规则
                classes = rule.get("classes")
                if classes:
                    node_classes = node.get("class", [])
                    if isinstance(node_classes, str):
                        node_classes = [node_classes]
                    # classes 列表内为 AND 关系（必须全部匹配）
                    if not all(cls in node_classes for cls in classes):
                        should_remove = False

                # 处理 id 规则
                ids = rule.get("ids")
                if ids:
                    node_id = node.get("id", "")
                    # ids 列表内为 AND 关系（必须全部匹配）
                    if not node_id or not all(id_val in node_id for id_val in ids):
                        should_remove = False

                # 如果没有任何过滤条件，则不删除
                if not any([styles, classes, ids]):
                    should_remove = False

                if should_remove:
                    nodes_to_remove.append(node)

            # 统一删除，避免边遍历边修改导致遗漏
            for node in nodes_to_remove:
                try:
                    node.decompose()
                except Exception:
                    pass
    except Exception:
        pass


def _get_account_specific_style_rules(account_name: str | None) -> list[dict]:
    """
    根据公众号名称获取过滤规则（包含通用规则和特定规则）

    规则格式说明：
    - 每个规则包含 'tag' 字段，以及以下过滤条件之一或多个：
      - 'styles': 样式列表
      - 'classes': CSS类名列表
      - 'ids': 元素ID列表
    - 同一条规则内，所有过滤条件都采用AND关系（必须全部匹配）
    - 多条规则为OR关系（满足任一规则即删除）

    使用示例：
    要为某个公众号添加特殊过滤规则，只需在 ACCOUNT_SPECIFIC_RULES 中添加对应的条目
    """

    # 通用过滤规则（对所有公众号生效）
    GENERAL_RULES = [
        # 样式过滤规则
        # {'tag': 'section', 'styles': ['border-width: 3px']},
        # {'tag': 'section', 'styles': ['background-color: rgb(239, 239, 239)']},
        # 类名过滤规则
        {"tag": "div", "classes": ["qr_code_pc", "qr_code_pc_inner"]},
        # ID过滤规则
        # {'tag': 'div', 'ids': ['ad-banner', 'promotion-box']},
    ]

    # 按公众号名称分类的特定样式过滤规则
    # 格式：{'公众号名称': [规则列表]}
    ACCOUNT_SPECIFIC_RULES = {
        # 示例规则（请根据实际需要修改或添加）：
        # '某个公众号名称': [
        #     # ID过滤
        #     {'tag': 'div', 'ids': ['footer-ads']},
        #     # 类名过滤：必须同时具有两个类名
        #     {'tag': 'div', 'classes': ['advertisement', 'sponsored']},
        #     # 样式过滤：必须同时匹配两个样式
        #     {'tag': 'p', 'styles': ['color: #999999', 'font-size: 12px']},
        #     # 组合过滤：必须同时满足样式和类名条件
        #     {'tag': 'section', 'styles': ['border-width: 3px'], 'classes': ['promo-box']},
        # ],
        # '另一个公众号': [
        #     # 如需OR关系，写多条规则：
        #     {'tag': 'span', 'styles': ['display: none']},  # 规则1：隐藏的span
        #     {'tag': 'div', 'styles': ['visibility: hidden']},  # 规则2：隐藏的div
        #     {'tag': 'section', 'classes': ['advertisement']},  # 规则3：广告类名的section
        #     {'tag': 'section', 'classes': ['sponsored']},  # 规则4：赞助类名的section
        # ],
        "央视财经": [
            {"tag": "div", "classes": ["js_mpvedio_wrapper_wxv_4156197472454262787"]},
            {"tag": "section", "classes": ["js_darkmode__21"]},
        ],
        "券商中国": [
            {"tag": "img", "classes": ["rich_pages", "wxw-img", "__bg_gif"]},
            {"tag": "section", "classes": ["border: 1px solid rgb(170, 166, 149)"]},
            {
                "tag": "section",
                "styles": [
                    "caret-color: rgb(255, 0, 0)",
                    "color: rgb(163, 163, 163)",
                    "text-align: center",
                    "widows: 1",
                    "line-height: 25.0746px",
                ],
            },
            {
                "tag": "section",
                "styles": [
                    "background-color: rgb(220, 194, 131)",
                    "border: 1px solid rgb(170, 166, 149)",
                ],
            },
        ],
        "中国基金报": [
            {"tag": "img", "classes": ["rich_pages", "wxw-img", "__bg_gif"]},
        ],
        "一瑜中的": [
            {"tag": "section", "styles": ["border-width: 3px"]},
            {"tag": "section", "styles": ["background-color: rgb(239, 239, 239)"]},
        ],
    }
    # 合并所有规则
    all_rules = GENERAL_RULES.copy()
    if account_name and account_name in ACCOUNT_SPECIFIC_RULES:
        all_rules.extend(ACCOUNT_SPECIFIC_RULES[account_name])

    return all_rules


def _clean_and_normalize_weixin_content(content_elem, account_name: str | None = None) -> None:
    """清洗与标准化微信正文容器（可持续完善规则）。"""
    # 懒加载图片与占位符
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

    # 应用过滤规则移除特定 tag 元素
    removal_rules = _get_account_specific_style_rules(account_name)
    if removal_rules:
        _apply_removal_rules(content_elem, removal_rules)


def _process_weixin_content(
    html: str, title: str | None = None, url: str | None = None
) -> FetchResult:
    """处理微信内容，提取标题、作者、发布日期和正文"""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"BeautifulSoup解析失败: {e}")
        return FetchResult(title=None, html_markdown="")

    # 头部信息
    title, account_name, header_parts = _build_weixin_header_parts(soup, url, title)
    header_str = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    # 正文：定位并构建正文容器
    content_elem = _build_weixin_content_element(soup)

    # 清洗与标准化正文（规则可持续完善）
    if content_elem:
        _clean_and_normalize_weixin_content(content_elem, account_name)
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


def fetch_weixin_article(
    session,
    url: str,
    logger: Optional[ConvertLogger] = None,
    shared_browser: Any | None = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> FetchResult:
    """
    获取微信公众号文章内容 - 仅使用 Playwright

    采用 Playwright 浏览器自动化（可处理 poc_token 验证），并带重试。
    """

    max_retries = 2

    for retry in range(max_retries):
        try:
            if should_stop and should_stop():
                raise StopRequested()
            if retry > 0:
                if logger:
                    logger.fetch_retry("微信策略", retry, max_retries)
                # stop-aware sleep
                total_sleep = random.uniform(3, 6)
                slept = 0.0
                while slept < total_sleep:
                    if should_stop and should_stop():
                        raise StopRequested()
                    step = min(0.2, total_sleep - slept)
                    time.sleep(step)
                    slept += step
            else:
                if logger:
                    logger.fetch_start("微信策略")

            if should_stop and should_stop():
                raise StopRequested()
            result = _try_playwright_crawler(url, logger, shared_browser, should_stop)
            if result.success:
                if logger:
                    logger.fetch_success()
                    logger.parse_start()
                if should_stop and should_stop():
                    raise StopRequested()
                processed_result = _process_weixin_content(result.text_content, result.title, url)
                if logger:
                    logger.clean_start()

                content = processed_result.html_markdown or ""
                if content and (
                    "环境异常" in content or "完成验证" in content or "去验证" in content
                ):
                    if logger:
                        logger.warning("[解析] 检测到验证页面，重试...")
                    if retry < max_retries - 1:
                        continue
                    break

                if processed_result.title and (
                    "环境异常" in processed_result.title or "验证" in processed_result.title
                ):
                    if logger:
                        logger.warning("[解析] 标题包含验证信息，重试...")
                    if retry < max_retries - 1:
                        continue
                    break

                if processed_result.title and logger:
                    logger.parse_title(processed_result.title)
                if logger:
                    logger.convert_start()
                    logger.convert_success()
                return processed_result
            else:
                if retry < max_retries - 1:
                    continue
                break
        except StopRequested:
            # Short-circuit to service layer; it will emit a 'stopped' event
            raise
        except Exception as e:
            if retry < max_retries - 1:
                continue
            break

    raise Exception("微信内容获取失败，回退到通用转换器")
