from __future__ import annotations

from typing import Callable
import os

from markitdown_app.core.handlers.generic_handler import convert_url
from markitdown_app.core.handlers.weixin_handler import fetch_weixin_article
from markitdown_app.core.handlers.zhihu_handler import fetch_zhihu_article
from markitdown_app.core.handlers.wordpress_handler import fetch_wordpress_article
from markitdown_app.core.handlers.nextjs_handler import fetch_nextjs_article
from markitdown_app.core.images import download_images_and_rewrite
from markitdown_app.core.filename import derive_md_filename
from markitdown_app.core.normalize import normalize_markdown_headings
from markitdown_app.app_types import ConvertPayload, ConversionOptions, ConvertResult


Handler = Callable[[ConvertPayload, any, ConversionOptions], ConvertResult | None]


def _weixin_handler(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult | None:
    url = payload.value
    if "mp.weixin.qq.com" not in url:
        return None
    # 透传 UI 提示回调到 weixin handler，用于状态栏显示
    on_detail_cb = payload.meta.get("on_detail")
    fetched = fetch_weixin_article(session, url, on_detail=on_detail_cb)

    # If blocked or empty, fallback to generic converter
    # 更智能的阻塞检测：只有在内容很短且包含验证关键词时才认为是阻塞
    blocked_indicators = ["环境异常", "验证", "需完成验证"]
    content = fetched.html_markdown or ""
    
    if not content.strip():
        return None
    
    # 如果内容长度大于1000字符，即使包含验证关键词也认为是正常内容
    if len(content) > 1000:
        pass  # 内容足够长，认为是正常文章
    elif (fetched.title and any(k in fetched.title for k in blocked_indicators)) or any(
        k in content for k in blocked_indicators
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


def _zhihu_handler(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult | None:
    url = payload.value
    if "zhuanlan.zhihu.com" not in url and "zhihu.com" not in url:
        return None
    
    try:
        on_detail_cb = payload.meta.get("on_detail")
        fetched = fetch_zhihu_article(session, url, on_detail=on_detail_cb)

        # 更智能的阻塞检测：只有在内容很短且包含验证关键词时才认为是阻塞
        content = fetched.html_markdown or ""
        blocked_indicators = ["验证", "登录", "访问被拒绝", "403", "404", "页面不存在", "知乎", "zhihu"]
        
        if not content.strip():
            return None
        
        # 如果内容足够长，认为是正常文章
        if len(content) > 1000:
            pass  # 内容足够长，认为是正常文章
        elif (fetched.title and any(k in fetched.title for k in blocked_indicators)) or any(
            k in content for k in blocked_indicators
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
    except Exception as e:
        # 如果知乎处理器失败，返回None让系统回退到通用转换器
        print(f"Zhihu handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _wordpress_handler(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult | None:
    """WordPress网站处理器 - 专门处理skywind.me/blog等WordPress站点"""
    url = payload.value
    
    # 检查是否是WordPress站点（特别是skywind.me/blog）
    if "skywind.me/blog" not in url and not _is_wordpress_site(url):
        return None
    
    try:
        fetched = fetch_wordpress_article(session, url)

        # 检查内容质量
        content = fetched.html_markdown or ""
        if not content.strip():
            return None
        
        # 如果内容太短，可能没有正确提取
        if len(content) < 200:
            print(f"WordPress内容太短 ({len(content)} 字符)，可能提取失败")
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
    except Exception as e:
        # 如果WordPress处理器失败，返回None让系统回退到通用转换器
        print(f"WordPress handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _nextjs_handler(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult | None:
    """Next.js Blog 处理器 - 专门处理 guangzhengli.com/blog"""
    url = payload.value
    # 目前仅针对 guangzhengli 博客域名启用
    if "guangzhengli.com/blog" not in url:
        return None

    try:
        fetched = fetch_nextjs_article(session, url)

        content = fetched.html_markdown or ""
        if not content.strip():
            return None

        if len(content) < 200:
            print(f"Next.js内容太短 ({len(content)} 字符)，可能提取失败")
            return None

        text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                on_detail_cb = payload.meta.get("on_detail")
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    on_detail=on_detail_cb,
                )

        filename = derive_md_filename(fetched.title, url)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        print(f"Next.js handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None

def _is_wordpress_site(url: str) -> bool:
    """简单检测是否是WordPress站点"""
    # 这里可以添加更多WordPress站点的检测逻辑
    # 目前主要针对skywind.me，但可以扩展
    wordpress_indicators = [
        "wordpress.com",
        "wp-content",
        "/wp-",
        "wp-includes"
    ]
    return any(indicator in url.lower() for indicator in wordpress_indicators)


HANDLERS: list[Handler] = [_weixin_handler, _zhihu_handler, _wordpress_handler, _nextjs_handler]


def convert(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    if payload.kind == "url":
        for h in HANDLERS:
            out = h(payload, session, options)
            if out is not None:
                return out
        return convert_url(payload, session, options)
    raise NotImplementedError(f"Unsupported payload kind: {payload.kind}")


