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
    no_proxy: bool
    download_images: bool


@dataclass
class ConvertResult:
    title: str | None
    markdown: str
    suggested_filename: str


@dataclass
class ProgressEvent:
    kind: Literal["status", "detail", "progress_init", "progress_step", "progress_done", "stopped", "error"]
    text: str | None = None
    total: int | None = None
    current: int | None = None


class ContentSourceHandler(Protocol):
    def can_handle(self, request: SourceRequest) -> bool: ...
    def fetch(self, request: SourceRequest, session: Any) -> Any: ...


class Converter(Protocol):
    def can_convert(self, payload: Any) -> bool: ...
    def convert(self, payload: Any, session: Any) -> ConvertResult: ...


@dataclass
class FetchResult:
    title: str | None
    html_markdown: str


@dataclass
class ConvertPayload:
    kind: Literal["url", "html", "file"]
    value: str
    meta: dict[str, Any] = field(default_factory=dict)


