from __future__ import annotations

from markitdown import MarkItDown

from markitdown_app.core.normalize import normalize_markdown_headings
from markitdown_app.core.filename import derive_md_filename
from markitdown_app.core.images import download_images_and_rewrite
from markitdown_app.types import ConvertPayload, ConversionOptions, ConvertResult


def convert_url(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    assert payload.kind == "url"
    url = payload.value

    md = MarkItDown(enable_plugins=False, requests_session=session)
    try:
        result = md.convert(url)
    except Exception:
        if url.lower().startswith("https://"):
            fallback = "http://" + url[8:]
            result = md.convert(fallback)
            url = fallback
        else:
            raise

    title = getattr(result, "title", None) or None
    text = result.text_content if getattr(result, "text_content", None) else str(result)
    text = normalize_markdown_headings(text, title)

    if options.download_images:
        images_dir = payload.meta.get("images_dir") or (payload.meta.get("out_dir") and (payload.meta["out_dir"] + "/img"))
        if images_dir:
            should_stop_cb = payload.meta.get("should_stop")
            on_detail_cb = payload.meta.get("on_detail")
            text = download_images_and_rewrite(
                text,
                url,
                images_dir,
                session,
                should_stop=should_stop_cb,
                on_detail=on_detail_cb,
            )

    filename = derive_md_filename(title, url)
    return ConvertResult(title=title, markdown=text, suggested_filename=filename)


