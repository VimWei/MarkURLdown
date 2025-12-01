"""普通网站URL转换器 - Playwright + MarkItDown 单策略实现"""

import time
from dataclasses import dataclass
from datetime import datetime

from markitdown import MarkItDown

from markdownall.app_types import ConversionOptions, ConvertPayload, ConvertResult
from markdownall.core.exceptions import StopRequested
from markdownall.core.filename import derive_md_filename
from markdownall.core.images import download_images_and_rewrite
from markdownall.core.normalize import normalize_markdown_headings


@dataclass
class CrawlerResult:
    """爬虫结果"""

    success: bool
    title: str | None
    text_content: str
    error: str | None = None


def _try_playwright_markitdown(url: str, session) -> CrawlerResult:
    """唯一策略：使用 Playwright 拉取 + MarkItDown 转换。"""
    # 为兼容在已有 asyncio 事件循环中的使用场景，这里改为使用 Playwright 的 async API，
    # 并在独立线程中运行事件循环，从而避免 “Sync API inside the asyncio loop” 错误。
    import asyncio
    import threading
    from queue import Queue

    async def _run_async() -> CrawlerResult:
        try:
            from playwright.async_api import async_playwright
        except Exception as e:  # Playwright 未安装或导入失败
            return CrawlerResult(
                success=False, title=None, text_content="", error=f"Playwright导入异常: {e}"
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 设置用户代理
                await page.set_extra_http_headers(
                    {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/91.0.4472.124 Safari/537.36"
                        )
                    }
                )

                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(2)  # 等待页面稳定

                # 获取页面内容
                html = await page.content()
                title = await page.title()

                await browser.close()

                # 使用MarkItDown处理HTML（兼容老版本，把“HTML字符串被当成文件路径”的问题也一并规避）
                md = MarkItDown()
                md._requests_session.headers.update({"Accept-Encoding": "gzip, deflate"})

                # 参考 _try_generic_with_filtering 的多重兜底策略，避免把长 HTML 当作路径导致
                # [Errno 2] No such file or directory: '<!DOCTYPE html>...'
                try:
                    result = md.convert(html)
                except Exception:
                    try:
                        # 尝试以字节传入
                        result = md.convert(html.encode("utf-8"))
                    except Exception:
                        # 最后兜底：写入临时文件，再把文件路径交给 MarkItDown
                        import os
                        import tempfile

                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
                        try:
                            tmp.write(html.encode("utf-8"))
                            tmp.close()
                            result = md.convert(tmp.name)
                        finally:
                            try:
                                os.unlink(tmp.name)
                            except Exception:
                                pass

                if result and result.text_content:
                    return CrawlerResult(
                        success=True, title=title, text_content=result.text_content
                    )
                else:
                    return CrawlerResult(
                        success=False, title=title, text_content="", error="MarkItDown处理HTML失败"
                    )
        except Exception:
            # 不再把异常对象直接拼到字符串里，避免把 HTML 之类的大文本内容泄露到日志
            return CrawlerResult(
                success=False, title=None, text_content="", error="Playwright运行异常"
            )

    # 在线程中启动一个新的事件循环来运行 async Playwright 逻辑，避免与当前线程的事件循环冲突。
    q: "Queue[CrawlerResult]" = Queue(maxsize=1)

    def _worker() -> None:
        try:
            result = asyncio.run(_run_async())
        except Exception:
            # 线程级别兜底，同样避免把异常对象（可能带有 HTML 内容）直接打到日志里
            result = CrawlerResult(
                success=False, title=None, text_content="", error="Playwright线程异常"
            )
        q.put(result)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()
    return q.get()


def convert_url(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    """转换普通网站URL为Markdown（Playwright单策略）"""
    assert payload.kind == "url"
    url = payload.value
    # Define logger and should_stop at function start to avoid scope issues and allow early abort
    logger = payload.meta.get("logger")
    should_stop = payload.meta.get("should_stop") or (lambda: False)

    def _check_stop():
        if should_stop():
            raise StopRequested()

    max_retries = 2
    for retry in range(max_retries):
        try:
            _check_stop()
            if retry == 0:
                if logger:
                    logger.fetch_start("Playwright策略")
            else:
                if logger:
                    logger.fetch_retry("Playwright策略", retry, max_retries)
                # Stop-aware sleep between retries
                sleep_total = 2.0
                slept = 0.0
                while slept < sleep_total:
                    _check_stop()
                    step = min(0.2, sleep_total - slept)
                    time.sleep(step)
                    slept += step

            _check_stop()
            result = _try_playwright_markitdown(url, session)
            if result.success and result.text_content and len(result.text_content.strip()) > 100:
                if logger:
                    logger.fetch_success()
                    logger.parse_start()
                    if result.title:
                        logger.parse_title(result.title)
                    logger.clean_start()
                    logger.convert_start()

                _check_stop()
                text = normalize_markdown_headings(result.text_content, result.title)
                conversion_timestamp = datetime.now()

                if options.download_images:
                    images_dir = payload.meta.get("images_dir") or (
                        payload.meta.get("out_dir") and (payload.meta["out_dir"] + "/img")
                    )
                    if images_dir:
                        text = download_images_and_rewrite(
                            text,
                            url,
                            images_dir,
                            session,
                            should_stop=should_stop,
                            logger=logger,
                            timestamp=conversion_timestamp,
                        )

                filename = derive_md_filename(result.title, url, conversion_timestamp)
                if logger:
                    logger.convert_success()
                return ConvertResult(title=result.title, markdown=text, suggested_filename=filename)

            if logger:
                logger.warning("[解析] Playwright策略获取到无效内容，重试中...")

        except Exception:
            if retry < max_retries - 1:
                continue
            if logger:
                logger.fetch_failed("Playwright策略", "异常")
            break

    raise Exception("Playwright策略获取失败")
