from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from markdownall.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markdownall.services.convert_service import ConvertService

OnEvent = Callable[[ProgressEvent], None]


@dataclass
class ViewState:
    status_text: str = "准备就绪"
    detail_text: str = ""
    total: int = 0
    current: int = 0


class ViewModel:
    def __init__(self) -> None:
        self.state = ViewState()
        self._service = ConvertService()

    def start(
        self,
        requests_list: list[SourceRequest],
        out_dir: str,
        options: ConversionOptions,
        on_event: OnEvent,
        signals=None,
        ui_logger: object | None = None,
    ) -> None:
        self._service.run(requests_list, out_dir, options, on_event, signals, ui_logger)

    def stop(self, on_event: OnEvent) -> None:
        self._service.stop()
        on_event(ProgressEvent(kind="stopped", text="转换已请求停止"))
