from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from markitdown_app.services.convert_service import ConvertService
from markitdown_app.types import ProgressEvent, SourceRequest, ConversionOptions


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

    def start(self, requests_list: list[SourceRequest], out_dir: str, options: ConversionOptions, on_event: OnEvent) -> None:
        self._service.run(requests_list, out_dir, options, on_event)

    def stop(self, on_event: OnEvent) -> None:
        self._service.stop()
        on_event(ProgressEvent(kind="stopped", text="转换已请求停止"))


