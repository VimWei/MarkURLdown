from __future__ import annotations

from typing import Callable
import os

from markitdown_app.core.url_converter import convert_url
from markitdown_app.core.weixin_handler import fetch_weixin_article
from markitdown_app.core.images import download_images_and_rewrite
from markitdown_app.core.filename import derive_md_filename
from markitdown_app.core.normalize import normalize_markdown_headings
from markitdown_app.types import ConvertPayload, ConversionOptions, ConvertResult


Handler = Callable[[ConvertPayload, any, ConversionOptions], ConvertResult | None]


def _weixin_handler(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult | None:
    url = payload.value
    if "mp.weixin.qq.com" not in url:
        return None
    fetched = fetch_weixin_article(session, url)

    # If blocked or empty, fallback to generic converter
    blocked_indicators = ["环境异常", "验证", "需完成验证"]
    if not (fetched.html_markdown or "").strip():
        return None
    if (fetched.title and any(k in fetched.title for k in blocked_indicators)) or any(
        k in (fetched.html_markdown or "") for k in blocked_indicators
    ):
        return None

    text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

    if options.download_images:
        images_dir = payload.meta.get("images_dir")
        if not images_dir and payload.meta.get("out_dir"):
            images_dir = os.path.join(payload.meta["out_dir"], "img")
        if images_dir:
            should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
            on_detail_cb = payload.meta.get("on_detail")
            text = download_images_and_rewrite(text, url, images_dir, session, should_stop=should_stop_cb, on_detail=on_detail_cb)

    filename = derive_md_filename(fetched.title, url)
    return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)


HANDLERS: list[Handler] = [_weixin_handler]


def convert(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    if payload.kind == "url":
        for h in HANDLERS:
            out = h(payload, session, options)
            if out is not None:
                return out
        return convert_url(payload, session, options)
    raise NotImplementedError(f"Unsupported payload kind: {payload.kind}")


