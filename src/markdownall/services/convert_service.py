from __future__ import annotations

import os
import threading
from typing import Callable

from markdownall.app_types import (
    ConversionOptions,
    ConvertPayload,
    ProgressEvent,
    SourceRequest,
)
from markdownall.core.registry import convert as registry_convert
from markdownall.io.logger import log_urls
from markdownall.io.session import build_requests_session
from markdownall.io.writer import write_markdown

EventCallback = Callable[[ProgressEvent], None]


class LoggerAdapter:
    """将服务层日志调用适配到 UI(LogPanel) 的轻量适配器（线程安全）。

    优先通过 ConvertService 提供的 signals 将日志事件发往主线程；
    若无 signals，则在主线程直接调用 UI；在后台线程降级为 print。
    """

    def __init__(self, ui: object | None, signals=None):
        # 期望 ui 暴露: log_info/log_success/log_warning/log_error
        self._ui = ui
        self._signals = signals

    def _emit_progress(self, kind: str, key: str | None = None, text: str | None = None, data: dict | None = None) -> None:
        # 尽量使用 signals 将事件发到主线程
        try:
            if self._signals is not None and hasattr(self._signals, "progress_event"):
                from markdownall.app_types import ProgressEvent

                ev = ProgressEvent(kind=kind, key=key, text=text, data=data)
                try:
                    self._signals.progress_event.emit(ev)
                    return
                except Exception:
                    pass
        except Exception:
            pass

        # 无 signals 或信号失败：尝试直接 UI 调用（仅主线程）或降级为打印
        self._call(kind, text or (data and str(data)) or "")

    def _call(self, method: str, message: str) -> None:
        # 避免在工作线程直接调用 UI，导致 Qt 线程冲突并崩溃
        try:
            import threading
            if self._ui is not None and threading.current_thread().name == "MainThread":
                # 将 kind 映射到 UI 的 log_* 方法
                ui_method = None
                if method in ("status", "detail"):
                    ui_method = getattr(self._ui, "log_info", None)
                elif method == "progress_done":
                    ui_method = getattr(self._ui, "log_success", None)
                elif method == "error":
                    ui_method = getattr(self._ui, "log_error", None)
                else:
                    ui_method = getattr(self._ui, "log_info", None)
                if callable(ui_method):
                    ui_method(message)
            else:
                # 后台线程：降级输出
                print(message)
        except Exception:
            pass

    def info(self, msg: str) -> None:
        # 普通信息 -> status 事件
        self._emit_progress(kind="status", text=msg)

    def success(self, msg: str) -> None:
        self._emit_progress(kind="detail", text=msg)

    def warning(self, msg: str) -> None:
        self._emit_progress(kind="detail", text=f"⚠️ {msg}")

    def error(self, msg: str) -> None:
        self._emit_progress(kind="error", text=f"❌ {msg}")

    # 任务分组日志（如果 UI 提供 appendTaskLog/appendMultiTaskSummary 则使用之）
    def task_status(self, idx: int, total: int, url: str) -> None:
        try:
            self._emit_progress(
                kind="status",
                data={"url": url, "idx": idx, "total": total},
                text=f"Processing: {url}",
            )
        except Exception:
            print(f"Processing: {url}")

    def images_progress(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None:
        try:
            self._emit_progress(
                kind="status",
                key="images_dl_progress",
                data={"total": total, "task_idx": task_idx, "task_total": task_total},
                text=f"[图片] 发现 {total} 张图片，开始下载...",
            )
        except Exception:
            print(f"[图片] 发现 {total} 张图片，开始下载...")

    def images_done(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None:
        try:
            self._emit_progress(
                kind="status",
                key="images_dl_done",
                data={"total": total, "task_idx": task_idx, "task_total": task_total},
                text=f"[图片] 下载完成: {total} 张图片",
            )
        except Exception:
            print(f"[图片] 下载完成: {total} 张图片")

    def debug(self, msg: str) -> None:
        self._emit_progress(kind="status", text=msg)

    # 细粒度阶段日志方法
    def fetch_start(self, strategy_name: str, retry: int = 0, max_retries: int = 0) -> None:
        if retry > 0:
            msg = f"[抓取] {strategy_name}重试 {retry}/{max_retries-1}..."
        else:
            msg = f"[抓取] {strategy_name}..."
        self._emit_progress(kind="status", text=msg)

    def fetch_success(self, content_length: int = 0) -> None:
        msg = "[抓取] 成功获取内容"
        if content_length > 0:
            msg += f" (内容长度: {content_length} 字符)"
        self._emit_progress(kind="status", text=msg)

    def fetch_failed(self, strategy_name: str, error: str) -> None:
        msg = f"[抓取] {strategy_name}策略失败: {error}"
        self._emit_progress(kind="detail", text=msg)

    def fetch_retry(self, strategy_name: str, retry: int, max_retries: int) -> None:
        msg = f"[抓取] {strategy_name}重试 {retry}/{max_retries-1}..."
        self._emit_progress(kind="status", text=msg)

    def parse_start(self) -> None:
        self._emit_progress(kind="status", text="[解析] 提取标题和正文...")

    def parse_title(self, title: str) -> None:
        self._emit_progress(kind="status", text=f"[解析] 标题: {title}")

    def parse_content_short(self, length: int, min_length: int = 200) -> None:
        self._emit_progress(kind="detail", text=f"[解析] 内容太短 ({length} 字符)，尝试下一个策略")

    def parse_success(self, content_length: int) -> None:
        self._emit_progress(kind="status", text=f"[解析] 解析成功，内容长度: {content_length} 字符")

    def clean_start(self) -> None:
        self._emit_progress(kind="status", text="[清理] 移除广告和无关内容...")

    def clean_success(self) -> None:
        self._emit_progress(kind="status", text="[清理] 内容清理完成")

    def convert_start(self) -> None:
        self._emit_progress(kind="status", text="[转换] 转换为Markdown...")

    def convert_success(self) -> None:
        # 移除冗余的转换完成日志，转换开始已经足够
        pass

    def url_success(self, title: str) -> None:
        self._emit_progress(kind="detail", text=f"✅ URL处理成功: {title}")

    def url_failed(self, url: str, error: str) -> None:
        self._emit_progress(kind="error", text=f"❌ URL处理失败: {url} - {error}")

    def batch_start(self, total: int) -> None:
        self._emit_progress(kind="status", text=f"🚀 开始批量处理 {total} 个URL...")

    def batch_summary(self, success: int, failed: int, total: int) -> None:
        # 静默处理，统计信息将合并到 Multi-task completed 消息中
        pass


class ConvertService:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._should_stop = False
        self._signals = None  # 用于存储UI信号对象

    def run(
        self,
        requests_list: list[SourceRequest],
        out_dir: str,
        options: ConversionOptions,
        on_event: EventCallback,
        signals=None,
        ui_logger: object | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._should_stop = False
        self._signals = signals  # 存储信号对象
        # Log all URLs for this run into today's log file
        try:
            urls = [
                r.value
                for r in requests_list
                if getattr(r, "kind", None) == "url" and isinstance(r.value, str)
            ]
            log_urls(urls)
        except Exception:
            pass
        self._thread = threading.Thread(
            target=self._worker, args=(requests_list, out_dir, options, on_event, ui_logger), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._should_stop = True

    def _emit_event_safe(self, event: ProgressEvent, on_event: EventCallback) -> None:
        """线程安全的事件发送方法"""
        try:
            if self._signals is not None:
                # 使用信号槽机制，确保线程安全
                self._signals.progress_event.emit(event)
            else:
                # 回退到直接调用（向后兼容）
                on_event(event)
        except Exception as e:
            print(f"Error emitting event: {e}")
            # 如果信号发送失败，尝试直接调用
            try:
                on_event(event)
            except Exception as e2:
                print(f"Error in fallback event call: {e2}")

    # Placeholder worker; implementation will arrive in later steps
    def _worker(
        self,
        requests_list: list[SourceRequest],
        out_dir: str,
        options: ConversionOptions,
        on_event: EventCallback,
        ui_logger: object | None,
    ) -> None:
        try:
            logger = LoggerAdapter(ui_logger, self._signals)
            total = len(requests_list)
            logger.batch_start(total)
            self._emit_event_safe(
                ProgressEvent(
                    kind="progress_init", total=total, key="convert_init", data={"total": total}
                ),
                on_event,
            )
            session = build_requests_session(
                ignore_ssl=options.ignore_ssl, use_proxy=options.use_proxy
            )

            # 可选：共享 Browser （加速模式）
            playwright_runtime = None
            shared_browser = None
            if getattr(options, "use_shared_browser", False):
                try:
                    from playwright.sync_api import sync_playwright

                    playwright_runtime = sync_playwright().start()
                    # 采用与独立浏览器一致的启动选项，提升反检测能力
                    shared_browser = playwright_runtime.chromium.launch(
                        headless=True,
                        channel="chrome",
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor",
                            "--disable-gpu",
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--disable-extensions",
                            "--disable-plugins",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                        ],
                    )
                    # 发出共享浏览器启动的细粒度事件
                    self._emit_event_safe(
                        ProgressEvent(kind="detail", key="convert_shared_browser_started", text="Shared browser started"),
                        on_event,
                    )
                except Exception as _e:
                    # 失败则降级为非共享路径
                    shared_browser = None

            completed = 0
            for idx, req in enumerate(requests_list, start=1):
                if self._should_stop:
                    self._emit_event_safe(
                        ProgressEvent(kind="stopped", key="convert_stopped"), on_event
                    )
                    return
                logger.task_status(idx, total, req.value)

                # 为当前任务构建一个带有任务上下文的 Logger 代理，自动注入 task_idx/task_total
                class _TaskAwareLogger:
                    def __init__(self, base_logger, task_idx: int, task_total: int):
                        self._base = base_logger
                        self._task_idx = task_idx
                        self._task_total = task_total

                    # 基础信息透传
                    def info(self, msg: str) -> None:
                        self._base.info(msg)

                    def success(self, msg: str) -> None:
                        self._base.success(msg)

                    def warning(self, msg: str) -> None:
                        self._base.warning(msg)

                    def error(self, msg: str) -> None:
                        self._base.error(msg)

                    def task_status(self, t_idx: int, t_total: int, url: str) -> None:
                        self._base.task_status(t_idx, t_total, url)

                    # 注入任务上下文的图片事件
                    def images_progress(self, total_imgs: int, task_idx: int | None = None, task_total: int | None = None) -> None:
                        self._base.images_progress(
                            total_imgs,
                            task_idx=self._task_idx if task_idx is None else task_idx,
                            task_total=self._task_total if task_total is None else task_total,
                        )

                    def images_done(self, total_imgs: int, task_idx: int | None = None, task_total: int | None = None) -> None:
                        self._base.images_done(
                            total_imgs,
                            task_idx=self._task_idx if task_idx is None else task_idx,
                            task_total=self._task_total if task_total is None else task_total,
                        )

                    def debug(self, msg: str) -> None:
                        self._base.debug(msg)

                    # 细粒度阶段日志方法
                    def fetch_start(self, strategy_name: str, retry: int = 0, max_retries: int = 0) -> None:
                        self._base.fetch_start(strategy_name, retry, max_retries)

                    def fetch_success(self, content_length: int = 0) -> None:
                        self._base.fetch_success(content_length)

                    def fetch_failed(self, strategy_name: str, error: str) -> None:
                        self._base.fetch_failed(strategy_name, error)

                    def fetch_retry(self, strategy_name: str, retry: int, max_retries: int) -> None:
                        self._base.fetch_retry(strategy_name, retry, max_retries)

                    def parse_start(self) -> None:
                        self._base.parse_start()

                    def parse_title(self, title: str) -> None:
                        self._base.parse_title(title)

                    def parse_content_short(self, length: int, min_length: int = 200) -> None:
                        self._base.parse_content_short(length, min_length)

                    def parse_success(self, content_length: int) -> None:
                        self._base.parse_success(content_length)

                    def clean_start(self) -> None:
                        self._base.clean_start()

                    def clean_success(self) -> None:
                        self._base.clean_success()

                    def convert_start(self) -> None:
                        self._base.convert_start()

                    def convert_success(self) -> None:
                        self._base.convert_success()

                    def url_success(self, title: str) -> None:
                        self._base.url_success(title)

                    def url_failed(self, url: str, error: str) -> None:
                        self._base.url_failed(url, error)

                    def batch_start(self, total: int) -> None:
                        self._base.batch_start(total)

                    def batch_summary(self, success: int, failed: int, total: int) -> None:
                        self._base.batch_summary(success, failed, total)

                task_logger = _TaskAwareLogger(logger, idx, total)

                # Handler级别的共享浏览器控制
                # 根据handler声明自动决定是否使用共享浏览器
                effective_shared_browser = shared_browser
                if req.kind == "url" and isinstance(req.value, str):
                    url = req.value
                    from markdownall.core.registry import (
                        should_use_shared_browser_for_url,
                    )

                    if not should_use_shared_browser_for_url(url):
                        # 当前URL的handler声明不使用共享浏览器，先关闭共享浏览器
                        handler_name = "Unknown"
                        try:
                            from markdownall.core.registry import get_handler_for_url

                            handler = get_handler_for_url(url)
                            if handler:
                                handler_name = handler.handler_name
                        except:
                            pass

                        if shared_browser is not None:
                            logger.info(f"[浏览器] {handler_name}需要独立浏览器，关闭共享浏览器")
                            try:
                                shared_browser.close()
                            except Exception:
                                pass
                            shared_browser = None
                            # 同时关闭playwright runtime
                            if playwright_runtime is not None:
                                try:
                                    playwright_runtime.stop()
                                except Exception:
                                    pass
                                playwright_runtime = None

                        # 使用同步等待，确保资源完全释放
                        try:
                            import time
                            time.sleep(0.1)  # 等待100ms
                        except Exception:
                            pass
                        effective_shared_browser = None

                payload = ConvertPayload(
                    kind=req.kind,
                    value=req.value,
                    meta={
                        "out_dir": out_dir,
                        # 新日志接口（带任务上下文）
                        "logger": task_logger,
                        "should_stop": lambda: self._should_stop,
                        # 根据handler类型决定是否传递共享浏览器
                        "shared_browser": effective_shared_browser,
                    },
                )
                try:
                    result = registry_convert(payload, session, options)
                    out_path = write_markdown(out_dir, result.suggested_filename, result.markdown)
                    completed += 1
                    # 发出带任务上下文的完成事件，便于UI进行多组归档
                    self._emit_event_safe(
                        ProgressEvent(
                            kind="detail",
                            key="convert_detail_done",
                            data={"title": result.title or "无标题", "idx": idx, "total": total},
                            text=f"✅ URL处理成功: {result.title or '无标题'}",
                        ),
                        on_event,
                    )
                    self._emit_event_safe(
                        ProgressEvent(
                            kind="progress_step",
                            current=completed,
                            key="convert_progress_step",
                            data={"completed": completed, "total": total},
                        ),
                        on_event,
                    )

                    # 如果刚处理完不使用共享浏览器的URL，需要重新创建共享浏览器供后续URL使用
                    if (
                        req.kind == "url"
                        and isinstance(req.value, str)
                        and not should_use_shared_browser_for_url(req.value)
                    ):
                        # 检查是否还有后续URL需要处理
                        remaining_urls = [
                            r
                            for r in requests_list[idx:]
                            if r.kind == "url"
                            and isinstance(r.value, str)
                            and should_use_shared_browser_for_url(r.value)
                        ]
                        if remaining_urls and getattr(options, "use_shared_browser", False):
                            handler_name = "Unknown"
                            try:
                                handler = get_handler_for_url(req.value)
                                if handler:
                                    handler_name = handler.handler_name
                            except:
                                pass

                            # 重新创建共享浏览器（静默处理）
                            try:
                                from playwright.sync_api import sync_playwright

                                playwright_runtime = sync_playwright().start()
                                shared_browser = playwright_runtime.chromium.launch(
                                    headless=True,
                                    channel="chrome",
                                    args=[
                                        "--no-sandbox",
                                        "--disable-dev-shm-usage",
                                        "--disable-blink-features=AutomationControlled",
                                        "--disable-web-security",
                                        "--disable-features=VizDisplayCompositor",
                                        "--disable-gpu",
                                        "--no-first-run",
                                        "--no-default-browser-check",
                                        "--disable-extensions",
                                        "--disable-plugins",
                                        "--disable-background-timer-throttling",
                                        "--disable-backgrounding-occluded-windows",
                                        "--disable-renderer-backgrounding",
                                    ],
                                )
                                self._emit_event_safe(
                                    ProgressEvent(kind="detail", key="convert_shared_browser_started", text="Shared browser restarted"),
                                    on_event,
                                )
                            except Exception:
                                shared_browser = None
                                playwright_runtime = None

                except Exception as e:
                    logger.url_failed(req.value, str(e))
                    # Continue processing remaining URLs instead of stopping
                    continue

            # 输出总体处理情况摘要
            failed_count = total - completed
            logger.batch_summary(completed, failed_count, total)

            self._emit_event_safe(
                ProgressEvent(
                    kind="progress_done",
                    key="convert_progress_done",
                    data={"completed": completed, "total": total},
                ),
                on_event,
            )
        finally:
            # 关闭共享 Browser（静默处理）
            try:
                if shared_browser is not None:
                    shared_browser.close()
            except Exception:
                pass
            try:
                if playwright_runtime is not None:
                    playwright_runtime.stop()
            except Exception:
                pass
            self._thread = None
