from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class SourceRequest:
    kind: Literal["url", "html", "file"]
    value: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionOptions:
    ignore_ssl: bool
    use_proxy: bool
    download_images: bool
    filter_site_chrome: bool
    use_shared_browser: bool = True


@dataclass
class ConvertResult:
    title: str | None
    markdown: str
    suggested_filename: str


@dataclass
class ProgressEvent:
    kind: Literal[
        "status", "detail", "progress_init", "progress_step", "progress_done", "stopped", "error"
    ]
    key: str | None = None
    data: dict | None = None
    text: str | None = None
    total: int | None = None
    current: int | None = None


class ContentSourceHandler(Protocol):
    def can_handle(self, request: SourceRequest) -> bool: ...
    def fetch(self, request: SourceRequest, session: Any) -> Any: ...


class Converter(Protocol):
    def can_convert(self, payload: Any) -> bool: ...
    def convert(self, payload: Any, session: Any) -> ConvertResult: ...


class ConvertLogger(Protocol):
    """用于在转换过程中输出日志到 UI(LogPanel) 的协议接口。"""

    def info(self, msg: str) -> None: ...
    def success(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def debug(self, msg: str) -> None: ...

    # 任务级别状态（可选）
    def task_status(self, idx: int, total: int, url: str) -> None: ...

    # 图片下载进度（可选）
    def images_progress(
        self, total: int, task_idx: int | None = None, task_total: int | None = None
    ) -> None: ...
    def images_done(
        self, total: int, task_idx: int | None = None, task_total: int | None = None
    ) -> None: ...

    # 细粒度阶段日志方法
    def fetch_start(self, strategy_name: str, retry: int = 0, max_retries: int = 0) -> None: ...
    def fetch_success(self, content_length: int = 0) -> None: ...
    def fetch_failed(self, strategy_name: str, error: str) -> None: ...
    def fetch_retry(self, strategy_name: str, retry: int, max_retries: int) -> None: ...

    def parse_start(self) -> None: ...
    def parse_title(self, title: str) -> None: ...
    def parse_content_short(self, length: int, min_length: int = 200) -> None: ...
    def parse_success(self, content_length: int) -> None: ...

    def clean_start(self) -> None: ...
    def clean_success(self) -> None: ...

    def convert_start(self) -> None: ...
    def convert_success(self) -> None: ...

    def url_success(self, title: str) -> None: ...
    def url_failed(self, url: str, error: str) -> None: ...

    def batch_start(self, total: int) -> None: ...
    def batch_summary(self, success: int, failed: int, total: int) -> None: ...


@dataclass
class FetchResult:
    title: str | None
    html_markdown: str


@dataclass
class ConvertPayload:
    kind: Literal["url", "html", "file"]
    value: str
    meta: dict[str, Any] = field(default_factory=dict)
