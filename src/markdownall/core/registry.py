from __future__ import annotations

import os
from datetime import datetime
from typing import Callable, Protocol

from markdownall.app_types import ConversionOptions, ConvertPayload, ConvertResult
from markdownall.core.filename import derive_md_filename
from markdownall.core.handlers.appinn_handler import fetch_appinn_article
from markdownall.core.handlers.generic_handler import convert_url
from markdownall.core.handlers.nextjs_handler import fetch_nextjs_article
from markdownall.core.handlers.sspai_handler import fetch_sspai_article
from markdownall.core.handlers.weixin_handler import fetch_weixin_article
from markdownall.core.handlers.wordpress_handler import fetch_wordpress_article
from markdownall.core.handlers.zhihu_handler import fetch_zhihu_article
from markdownall.core.images import download_images_and_rewrite
from markdownall.core.normalize import normalize_markdown_headings


class HandlerWrapper:
    """Handler包装器，支持元数据声明"""

    def __init__(self, func: Callable, name: str, prefers_shared_browser: bool = True):
        self.func = func
        self._name = name
        self._prefers_shared_browser = prefers_shared_browser

    def __call__(
        self, payload: ConvertPayload, session, options: ConversionOptions
    ) -> ConvertResult | None:
        return self.func(payload, session, options)

    @property
    def prefers_shared_browser(self) -> bool:
        """声明是否偏好使用共享浏览器"""
        return self._prefers_shared_browser

    @property
    def handler_name(self) -> str:
        """Handler名称，用于调试和日志"""
        return self._name


class Handler(Protocol):
    """Handler协议，支持共享浏览器偏好声明"""

    def __call__(
        self, payload: ConvertPayload, session, options: ConversionOptions
    ) -> ConvertResult | None: ...

    @property
    def prefers_shared_browser(self) -> bool:
        """声明是否偏好使用共享浏览器。默认为True（支持共享浏览器）"""
        return True

    @property
    def handler_name(self) -> str:
        """Handler名称，用于调试和日志"""
        return self.__class__.__name__


def _weixin_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    url = payload.value
    if "mp.weixin.qq.com" not in url:
        return None
    # 新日志接口
    logger = payload.meta.get("logger")
    # 透传共享 Browser（若开启加速模式）
    shared_browser = payload.meta.get("shared_browser")
    fetched = fetch_weixin_article(
        session,
        url,
        logger=logger,
        shared_browser=shared_browser,
        should_stop=payload.meta.get("should_stop"),
    )

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

    # 生成统一时间戳，确保markdown文件名和图片文件名一致
    conversion_timestamp = datetime.now()

    if options.download_images:
        images_dir = payload.meta.get("images_dir")
        if not images_dir and payload.meta.get("out_dir"):
            images_dir = os.path.join(payload.meta["out_dir"], "img")
        if images_dir:
            should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
            text = download_images_and_rewrite(
                text,
                url,
                images_dir,
                session,
                should_stop=should_stop_cb,
                logger=logger,
                timestamp=conversion_timestamp,
            )

    filename = derive_md_filename(fetched.title, url, conversion_timestamp)
    return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)


def _zhihu_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    url = payload.value
    if "zhuanlan.zhihu.com" not in url and "zhihu.com" not in url:
        return None

    try:
        logger = payload.meta.get("logger")
        shared_browser = payload.meta.get("shared_browser")
        fetched = fetch_zhihu_article(
            session,
            url,
            logger=logger,
            shared_browser=shared_browser,
            should_stop=payload.meta.get("should_stop"),
        )

        # 更智能的阻塞检测：只有在内容很短且包含验证关键词时才认为是阻塞
        content = fetched.html_markdown or ""
        blocked_indicators = [
            "验证",
            "登录",
            "访问被拒绝",
            "403",
            "404",
            "页面不存在",
            "知乎",
            "zhihu",
        ]

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

        # 生成统一时间戳，确保markdown文件名和图片文件名一致
        conversion_timestamp = datetime.now()

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    logger=logger,
                    timestamp=conversion_timestamp,
                )

        filename = derive_md_filename(fetched.title, url, conversion_timestamp)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        # 如果知乎处理器失败，返回None让系统回退到通用转换器
        print(f"Zhihu handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _wordpress_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    """WordPress网站处理器 - 专门处理skywind.me/blog等WordPress站点"""
    url = payload.value

    # 检查是否是WordPress站点（特别是skywind.me/blog）
    if "skywind.me/blog" not in url and not _is_wordpress_site(url):
        return None

    try:
        # 透传共享 Browser（若开启加速模式）
        shared_browser = payload.meta.get("shared_browser")
        logger = payload.meta.get("logger")
        fetched = fetch_wordpress_article(
            session,
            url,
            logger=logger,
            shared_browser=shared_browser,
            should_stop=payload.meta.get("should_stop"),
        )

        # 检查内容质量
        content = fetched.html_markdown or ""
        if not content.strip():
            return None

        text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

        # 生成统一时间戳，确保markdown文件名和图片文件名一致
        conversion_timestamp = datetime.now()

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                logger = payload.meta.get("logger")
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    logger=logger,
                    timestamp=conversion_timestamp,
                )

        filename = derive_md_filename(fetched.title, url, conversion_timestamp)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        # 如果WordPress处理器失败，返回None让系统回退到通用转换器
        print(f"WordPress handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _nextjs_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    """Next.js Blog 处理器 - 专门处理 guangzhengli.com/blog"""
    url = payload.value
    # 目前仅针对 guangzhengli 博客域名启用
    if "guangzhengli.com/blog" not in url:
        return None

    try:
        # 透传共享 Browser（若开启加速模式）
        shared_browser = payload.meta.get("shared_browser")
        logger = payload.meta.get("logger")
        fetched = fetch_nextjs_article(
            session,
            url,
            logger=logger,
            shared_browser=shared_browser,
            should_stop=payload.meta.get("should_stop"),
        )

        content = fetched.html_markdown or ""
        if not content.strip():
            return None

        text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

        # 生成统一时间戳，确保markdown文件名和图片文件名一致
        conversion_timestamp = datetime.now()

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                logger = payload.meta.get("logger")
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    logger=logger,
                    timestamp=conversion_timestamp,
                )

        filename = derive_md_filename(fetched.title, url, conversion_timestamp)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        print(f"Next.js handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _is_wordpress_site(url: str) -> bool:
    """简单检测是否是WordPress站点"""
    # 这里可以添加更多WordPress站点的检测逻辑
    # 目前主要针对skywind.me，但可以扩展
    wordpress_indicators = ["wordpress.com", "wp-content", "/wp-", "wp-includes"]
    return any(indicator in url.lower() for indicator in wordpress_indicators)


def _sspai_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    """少数派文章处理器"""
    url = payload.value
    if "sspai.com" not in url:
        return None

    try:
        logger = payload.meta.get("logger")
        # 透传共享 Browser（若开启加速模式）
        shared_browser = payload.meta.get("shared_browser")
        fetched = fetch_sspai_article(
            session,
            url,
            logger=logger,
            shared_browser=shared_browser,
            should_stop=payload.meta.get("should_stop"),
        )

        # 检查内容质量
        content = fetched.html_markdown or ""
        if not content.strip():
            return None

        # 如果内容长度大于1000字符，认为是正常文章
        if len(content) < 200:
            return None

        text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

        # 生成统一时间戳，确保markdown文件名和图片文件名一致
        conversion_timestamp = datetime.now()

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    logger=logger,
                    timestamp=conversion_timestamp,
                )

        filename = derive_md_filename(fetched.title, url, conversion_timestamp)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        print(f"少数派 handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


def _appinn_handler(
    payload: ConvertPayload, session, options: ConversionOptions
) -> ConvertResult | None:
    """appinn.com 文章处理器"""
    url = payload.value
    if "appinn.com" not in url:
        return None

    try:
        logger = payload.meta.get("logger")
        # 透传共享 Browser（若开启加速模式）
        shared_browser = payload.meta.get("shared_browser")
        fetched = fetch_appinn_article(
            session,
            url,
            logger=logger,
            shared_browser=shared_browser,
            should_stop=payload.meta.get("should_stop"),
        )

        # 检查内容质量
        content = fetched.html_markdown or ""
        if not content.strip():
            return None

        # 如果内容长度小于200字符，认为是无效内容
        if len(content) < 200:
            return None

        text = normalize_markdown_headings(fetched.html_markdown, fetched.title)

        # 生成统一时间戳，确保markdown文件名和图片文件名一致
        conversion_timestamp = datetime.now()

        if options.download_images:
            images_dir = payload.meta.get("images_dir")
            if not images_dir and payload.meta.get("out_dir"):
                images_dir = os.path.join(payload.meta["out_dir"], "img")
            if images_dir:
                should_stop_cb = payload.meta.get("should_stop") or (lambda: False)
                text = download_images_and_rewrite(
                    text,
                    url,
                    images_dir,
                    session,
                    should_stop=should_stop_cb,
                    logger=logger,
                    timestamp=conversion_timestamp,
                )

        filename = derive_md_filename(fetched.title, url, conversion_timestamp)
        return ConvertResult(title=fetched.title, markdown=text, suggested_filename=filename)
    except Exception as e:
        print(f"appinn.com handler failed: {e}")
        print("🔄 正在回退到通用转换器...")
        return None


HANDLERS: list[Handler] = [
    HandlerWrapper(
        _weixin_handler, "WeixinHandler", prefers_shared_browser=False
    ),  # 微信必须使用独立浏览器
    HandlerWrapper(
        _zhihu_handler, "ZhihuHandler", prefers_shared_browser=True
    ),  # 知乎支持共享浏览器
    HandlerWrapper(
        _wordpress_handler, "WordPressHandler", prefers_shared_browser=True
    ),  # WordPress支持共享浏览器
    HandlerWrapper(
        _nextjs_handler, "NextJSHandler", prefers_shared_browser=True
    ),  # NextJS支持共享浏览器
    HandlerWrapper(
        _sspai_handler, "SspaiHandler", prefers_shared_browser=True
    ),  # 少数派支持共享浏览器
    HandlerWrapper(
        _appinn_handler, "AppinnHandler", prefers_shared_browser=True
    ),  # appinn.com支持共享浏览器
]


def get_handler_for_url(url: str) -> Handler | None:
    """根据URL找到对应的handler，用于检查共享浏览器偏好"""
    if not url:
        return None

    # 直接通过URL模式匹配，避免调用handler函数
    url_lower = url.lower()

    for handler in HANDLERS:
        # 根据handler名称和URL模式进行匹配
        handler_name = handler.handler_name

        if handler_name == "WeixinHandler" and "mp.weixin.qq.com" in url_lower:
            return handler
        elif handler_name == "ZhihuHandler" and (
            "zhuanlan.zhihu.com" in url_lower or "zhihu.com" in url_lower
        ):
            return handler
        elif handler_name == "WordPressHandler" and (
            "skywind.me/blog" in url_lower or _is_wordpress_site(url)
        ):
            return handler
        elif handler_name == "NextJSHandler" and "guangzhengli.com/blog" in url_lower:
            return handler
        elif handler_name == "SspaiHandler" and "sspai.com" in url_lower:
            return handler
        elif handler_name == "AppinnHandler" and "appinn.com" in url_lower:
            return handler

    return None


def should_use_shared_browser_for_url(url: str) -> bool:
    """检查URL是否应该使用共享浏览器"""
    handler = get_handler_for_url(url)
    if handler is None:
        # 如果没有匹配的handler，使用默认行为（支持共享浏览器）
        return True

    return handler.prefers_shared_browser


def convert(payload: ConvertPayload, session, options: ConversionOptions) -> ConvertResult:
    if payload.kind == "url":
        for h in HANDLERS:
            out = h(payload, session, options)
            if out is not None:
                return out
        return convert_url(payload, session, options)
    raise NotImplementedError(f"Unsupported payload kind: {payload.kind}")
