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

                payload = ConvertPayload(kind=req.kind, value=req.value, meta={
                    "out_dir": out_dir,
                    "on_detail": _emit_detail,
                    "should_stop": lambda: self._should_stop,
                })
                try:
                    result = registry_convert(payload, session, options)
                    out_path = write_markdown(out_dir, result.suggested_filename, result.markdown)
                    completed += 1
                    on_event(ProgressEvent(kind="detail", key="convert_detail_done", data={"path": out_path}))
                    on_event(ProgressEvent(kind="progress_step", current=completed, key="convert_progress_step", data={"completed": completed, "total": total}))
                except Exception as e:
                    on_event(ProgressEvent(kind="error", key="convert_error", data={"url": req.value, "error": str(e)}))

            on_event(ProgressEvent(kind="progress_done", key="convert_progress_done", data={"completed": completed, "total": total}))
        finally:
            self._thread = None


