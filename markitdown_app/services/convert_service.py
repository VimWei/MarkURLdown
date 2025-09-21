from __future__ import annotations

import os
import threading
from typing import Callable

from markitdown_app.core.registry import convert as registry_convert
from markitdown_app.io.session import build_requests_session
from markitdown_app.io.writer import write_markdown
from markitdown_app.io.logger import log_urls
from markitdown_app.app_types import SourceRequest, ConversionOptions, ProgressEvent, ConvertPayload


EventCallback = Callable[[ProgressEvent], None]


class ConvertService:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._should_stop = False
        self._signals = None  # 用于存储UI信号对象

    def run(self, requests_list: list[SourceRequest], out_dir: str, options: ConversionOptions, on_event: EventCallback, signals=None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._should_stop = False
        self._signals = signals  # 存储信号对象
        # Log all URLs for this run into today's log file
        try:
            urls = [r.value for r in requests_list if getattr(r, "kind", None) == "url" and isinstance(r.value, str)]
            log_urls(urls)
        except Exception:
            pass
        self._thread = threading.Thread(target=self._worker, args=(requests_list, out_dir, options, on_event), daemon=True)
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
    def _worker(self, requests_list: list[SourceRequest], out_dir: str, options: ConversionOptions, on_event: EventCallback) -> None:
        try:
            total = len(requests_list)
            self._emit_event_safe(ProgressEvent(kind="progress_init", total=total, key="convert_init", data={"total": total}), on_event)
            session = build_requests_session(ignore_ssl=options.ignore_ssl, use_proxy=options.use_proxy)

            # 可选：共享 Browser （加速模式）
            playwright_runtime = None
            shared_browser = None
            if getattr(options, "use_shared_browser", False):
                try:
                    from playwright.sync_api import sync_playwright
                    playwright_runtime = sync_playwright().start()
                    # 采用通用、稳健的最小配置。站点特定选项在 new_context 时设置。
                    shared_browser = playwright_runtime.chromium.launch(headless=True)
                    self._emit_event_safe(ProgressEvent(kind="detail", key="convert_shared_browser_started"), on_event)
                except Exception as _e:
                    # 失败则降级为非共享路径
                    shared_browser = None

            completed = 0
            for idx, req in enumerate(requests_list, start=1):
                if self._should_stop:
                    self._emit_event_safe(ProgressEvent(kind="stopped", key="convert_stopped"), on_event)
                    return
                self._emit_event_safe(ProgressEvent(kind="status", key="convert_status_running", data={"idx": idx, "total": total, "url": req.value}), on_event)

                def _emit_detail(msg):
                    # Support either raw text (backward compatible) or a dict with {key, data}
                    try:
                        if isinstance(msg, dict):
                            self._emit_event_safe(ProgressEvent(kind="detail", key=msg.get("key"), data=msg.get("data")), on_event)
                        else:
                            self._emit_event_safe(ProgressEvent(kind="detail", text=str(msg)), on_event)
                    except Exception:
                        self._emit_event_safe(ProgressEvent(kind="detail", text=str(msg)), on_event)

                # Handler级别的共享浏览器控制
                # 根据handler声明自动决定是否使用共享浏览器
                effective_shared_browser = shared_browser
                if req.kind == "url" and isinstance(req.value, str):
                    url = req.value
                    from markitdown_app.core.registry import should_use_shared_browser_for_url
                    
                    if not should_use_shared_browser_for_url(url):
                        # 当前URL的handler声明不使用共享浏览器，先关闭共享浏览器
                        handler_name = "Unknown"
                        try:
                            from markitdown_app.core.registry import get_handler_for_url
                            handler = get_handler_for_url(url)
                            if handler:
                                handler_name = handler.handler_name
                        except:
                            pass
                        
                        if shared_browser is not None:
                            print(f"{handler_name}检测到，关闭共享浏览器以使用独立浏览器")
                            try:
                                shared_browser.close()
                                print("共享浏览器已关闭")
                            except Exception as e:
                                print(f"关闭共享浏览器时出错: {e}")
                            shared_browser = None
                            # 同时关闭playwright runtime
                            if playwright_runtime is not None:
                                try:
                                    playwright_runtime.stop()
                                    print("Playwright runtime已停止")
                                except Exception as e:
                                    print(f"停止Playwright runtime时出错: {e}")
                                playwright_runtime = None
                            
                        # 使用异步等待，确保资源完全释放
                        try:
                            import asyncio
                            asyncio.run(asyncio.sleep(0.1))  # 等待100ms
                            print("等待资源释放完成...")
                        except Exception as e:
                            print(f"异步等待时出错: {e}")
                        effective_shared_browser = None
                
                payload = ConvertPayload(kind=req.kind, value=req.value, meta={
                    "out_dir": out_dir,
                    "on_detail": _emit_detail,
                    "should_stop": lambda: self._should_stop,
                    # 根据handler类型决定是否传递共享浏览器
                    "shared_browser": effective_shared_browser,
                })
                try:
                    result = registry_convert(payload, session, options)
                    out_path = write_markdown(out_dir, result.suggested_filename, result.markdown)
                    completed += 1
                    self._emit_event_safe(ProgressEvent(kind="detail", key="convert_detail_done", data={"path": out_path}), on_event)
                    self._emit_event_safe(ProgressEvent(kind="progress_step", current=completed, key="convert_progress_step", data={"completed": completed, "total": total}), on_event)
                    
                    # 如果刚处理完不使用共享浏览器的URL，需要重新创建共享浏览器供后续URL使用
                    if req.kind == "url" and isinstance(req.value, str) and not should_use_shared_browser_for_url(req.value):
                        # 检查是否还有后续URL需要处理
                        remaining_urls = [r for r in requests_list[idx:] if r.kind == "url" and isinstance(r.value, str) and should_use_shared_browser_for_url(r.value)]
                        if remaining_urls and getattr(options, "use_shared_browser", False):
                            handler_name = "Unknown"
                            try:
                                handler = get_handler_for_url(req.value)
                                if handler:
                                    handler_name = handler.handler_name
                            except:
                                pass
                            
                            print(f"{handler_name}URL处理完成，重新创建共享浏览器供后续URL使用")
                            try:
                                from playwright.sync_api import sync_playwright
                                playwright_runtime = sync_playwright().start()
                                shared_browser = playwright_runtime.chromium.launch(headless=True)
                                self._emit_event_safe(ProgressEvent(kind="detail", key="convert_shared_browser_restarted"), on_event)
                                print("共享浏览器重新创建成功")
                            except Exception as e:
                                print(f"重新创建共享浏览器失败: {e}")
                                shared_browser = None
                                playwright_runtime = None
                                
                except Exception as e:
                    print(f"Error processing URL {req.value}: {e}")
                    import traceback
                    traceback.print_exc()
                    self._emit_event_safe(ProgressEvent(kind="error", key="convert_error", data={"url": req.value, "error": str(e)}), on_event)
                    # Continue processing remaining URLs instead of stopping
                    continue

            self._emit_event_safe(ProgressEvent(kind="progress_done", key="convert_progress_done", data={"completed": completed, "total": total}), on_event)
        finally:
            # 关闭共享 Browser
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


