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

    def run(self, requests_list: list[SourceRequest], out_dir: str, options: ConversionOptions, on_event: EventCallback) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._should_stop = False
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

    # Placeholder worker; implementation will arrive in later steps
    def _worker(self, requests_list: list[SourceRequest], out_dir: str, options: ConversionOptions, on_event: EventCallback) -> None:
        try:
            total = len(requests_list)
            on_event(ProgressEvent(kind="progress_init", total=total, key="convert_init", data={"total": total}))
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
                    on_event(ProgressEvent(kind="detail", key="convert_shared_browser_started"))
                except Exception as _e:
                    # 失败则降级为非共享路径
                    shared_browser = None

            completed = 0
            for idx, req in enumerate(requests_list, start=1):
                if self._should_stop:
                    on_event(ProgressEvent(kind="stopped", key="convert_stopped"))
                    return
                on_event(ProgressEvent(kind="status", key="convert_status_running", data={"idx": idx, "total": total, "url": req.value}))

                def _emit_detail(msg):
                    # Support either raw text (backward compatible) or a dict with {key, data}
                    try:
                        if isinstance(msg, dict):
                            on_event(ProgressEvent(kind="detail", key=msg.get("key"), data=msg.get("data")))
                        else:
                            on_event(ProgressEvent(kind="detail", text=str(msg)))
                    except Exception:
                        on_event(ProgressEvent(kind="detail", text=str(msg)))

                # Handler级别的共享浏览器控制
                # 某些handler（如微信）必须使用独立浏览器，即使全局开启共享浏览器
                effective_shared_browser = shared_browser
                if req.kind == "url" and isinstance(req.value, str):
                    url = req.value.lower()
                    if "mp.weixin.qq.com" in url:
                        # 微信URL需要独立浏览器，先关闭共享浏览器
                        if shared_browser is not None:
                            print("微信URL检测到，关闭共享浏览器以使用独立浏览器")
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
                    on_event(ProgressEvent(kind="detail", key="convert_detail_done", data={"path": out_path}))
                    on_event(ProgressEvent(kind="progress_step", current=completed, key="convert_progress_step", data={"completed": completed, "total": total}))
                    
                    # 如果刚处理完微信URL，需要重新创建共享浏览器供后续URL使用
                    if req.kind == "url" and isinstance(req.value, str) and "mp.weixin.qq.com" in req.value.lower():
                        # 检查是否还有后续URL需要处理
                        remaining_urls = [r for r in requests_list[idx:] if r.kind == "url" and isinstance(r.value, str) and "mp.weixin.qq.com" not in r.value.lower()]
                        if remaining_urls and getattr(options, "use_shared_browser", False):
                            print("微信URL处理完成，重新创建共享浏览器供后续URL使用")
                            try:
                                from playwright.sync_api import sync_playwright
                                playwright_runtime = sync_playwright().start()
                                shared_browser = playwright_runtime.chromium.launch(headless=True)
                                on_event(ProgressEvent(kind="detail", key="convert_shared_browser_restarted"))
                                print("共享浏览器重新创建成功")
                            except Exception as e:
                                print(f"重新创建共享浏览器失败: {e}")
                                shared_browser = None
                                playwright_runtime = None
                                
                except Exception as e:
                    on_event(ProgressEvent(kind="error", key="convert_error", data={"url": req.value, "error": str(e)}))

            on_event(ProgressEvent(kind="progress_done", key="convert_progress_done", data={"completed": completed, "total": total}))
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


