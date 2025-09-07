"""
普通网站URL转换器 - 多策略实现
基于微信和知乎的经验，采用多策略方案：轻量级MarkItDown -> 增强MarkItDown(Playwright) -> 直接httpx
"""

import time
import random
from dataclasses import dataclass
from markitdown import MarkItDown
from markitdown_app.app_types import ConvertPayload, ConversionOptions, ConvertResult
from markitdown_app.io.session import build_requests_session
from markitdown_app.core.normalize import normalize_markdown_headings
from markitdown_app.core.images import download_images_and_rewrite
from markitdown_app.core.filename import derive_md_filename


@dataclass
class CrawlerResult:
    """爬虫结果"""
    success: bool
    title: str | None
    text_content: str
    error: str | None = None


def _try_lightweight_markitdown(url: str, session) -> CrawlerResult:
    """策略1: 轻量级MarkItDown - 快速尝试，适合简单网站"""
    try:
        print("尝试轻量级MarkItDown...")
        md = MarkItDown()
        # 修复 MarkItDown 的 User-Agent 问题
        md._requests_session.headers.update({
            "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        })
        result = md.convert(url)
        
        if result and result.text_content:
            return CrawlerResult(
                success=True,
                title=getattr(result, 'title', None) or (result.metadata.get('title') if hasattr(result, 'metadata') and result.metadata else None),
                text_content=result.text_content
            )
        else:
            return CrawlerResult(success=False, title=None, text_content="", error="MarkItDown返回空内容")
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=f"MarkItDown异常: {e}")


def _try_enhanced_markitdown(url: str, session) -> CrawlerResult:
    """策略2: 增强MarkItDown - 使用Playwright，处理复杂网站"""
    try:
        print("尝试增强MarkItDown (Playwright)...")
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
            
            # 使用MarkItDown处理HTML
            md = MarkItDown()
            result = md.convert(html)
            
            if result and result.text_content:
                return CrawlerResult(
                    success=True,
                    title=title,
                    text_content=result.text_content
                )
            else:
                return CrawlerResult(success=False, title=title, text_content="", error="MarkItDown处理HTML失败")
                
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=f"Playwright异常: {e}")


def _try_direct_httpx(url: str, session) -> CrawlerResult:
        """策略3: 直接httpx - 最后备用策略"""
        try:
            print("尝试直接httpx...")
            import httpx
            
            # 使用与session相同的User-Agent
            headers = {
                "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            }
            
            # 如果session设置了no_proxy，则httpx也禁用代理
            client_kwargs = {"headers": headers}
            if hasattr(session, 'trust_env') and not session.trust_env:
                # httpx 0.28.1 使用 trust_env=False 来禁用代理
                client_kwargs["trust_env"] = False
            
            with httpx.Client(**client_kwargs) as client:
                response = client.get(url, timeout=30)
                response.raise_for_status()
                
                # 使用MarkItDown处理URL（直接传递URL而不是HTML内容）
                md = MarkItDown()
                # 修复 MarkItDown 的 User-Agent 问题
                md._requests_session.headers.update({
                    "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                })
                result = md.convert(url)
                
                if result and result.text_content:
                    return CrawlerResult(
                        success=True,
                        title=getattr(result, 'title', None) or (result.metadata.get('title') if hasattr(result, 'metadata') and result.metadata else None),
                        text_content=result.text_content
                    )
                else:
                    return CrawlerResult(success=False, title=None, text_content="", error="MarkItDown处理失败")
                    
        except Exception as e:
            return CrawlerResult(success=False, title=None, text_content="", error=f"httpx异常: {e}")


def convert_url(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    """转换普通网站URL为Markdown"""
    assert payload.kind == "url"
    url = payload.value

    # 多策略尝试顺序
    crawler_strategies = [
        lambda: _try_lightweight_markitdown(url, session),
        lambda: _try_enhanced_markitdown(url, session),
        lambda: _try_direct_httpx(url, session),
    ]

    # 多策略尝试，每个策略最多重试2次
    max_retries = 2

    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                if retry > 0:
                    print(f"尝试普通网站策略 {i} (重试 {retry}/{max_retries-1})...")
                    time.sleep(random.uniform(2, 4))
                else:
                    print(f"尝试普通网站策略 {i}...")

                result = strategy()
                if result.success:
                    # 内容质量检测 - 简单验证
                    if result.text_content and len(result.text_content.strip()) > 100:
                        print(f"策略 {i} 成功获取到有效内容!")

                        # 标准化处理
                        text = normalize_markdown_headings(result.text_content, result.title)

                        # 图片处理（可选）
                        if options.download_images:
                            images_dir = payload.meta.get("images_dir") or (payload.meta.get("out_dir") and (payload.meta["out_dir"] + "/img"))
                            if images_dir:
                                should_stop_cb = payload.meta.get("should_stop")
                                on_detail_cb = payload.meta.get("on_detail")
                                text = download_images_and_rewrite(
                                    text, url, images_dir, session,
                                    should_stop=should_stop_cb, on_detail=on_detail_cb
                                )

                        filename = derive_md_filename(result.title, url)
                        return ConvertResult(title=result.title, markdown=text, suggested_filename=filename)
                    else:
                        print(f"策略 {i} 获取到无效内容，重试...")
                        if retry < max_retries - 1:
                            continue
                        else:
                            print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                            break
                else:
                    print(f"策略 {i} 失败: {result.error}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                        break

            except Exception as e:
                print(f"策略 {i} 异常: {e}")
                if retry < max_retries - 1:
                    continue
                else:
                    print(f"策略 {i} 重试次数用尽，尝试下一个策略")
                    break

        # 策略间等待
        if i < len(crawler_strategies):
            time.sleep(random.uniform(1, 3))

    raise Exception("所有普通网站获取策略都失败")
