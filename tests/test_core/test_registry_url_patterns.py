from __future__ import annotations

import pytest

from markitdown_app.core.registry import (
    get_handler_for_url,
    should_use_shared_browser_for_url,
)


@pytest.mark.unit
def test_handler_detection_with_query_and_case():
    urls = [
        "HTTPS://MP.WEIXIN.QQ.COM/s/abc?utm=1",
        "https://zhuanlan.zhihu.com/p/1?x=1#frag",
        "https://Skywind.me/blog/archives/100?ref=abc",
        "https://GUANGZHENGLI.com/blog/hello?from=home",
        "https://SSPAI.com/post/123?foo=bar",
        "https://WWW.APPINN.COM/abcd?utm=2",
    ]
    expected = [
        ("WeixinHandler", False),
        ("ZhihuHandler", True),
        ("WordPressHandler", True),
        ("NextJSHandler", True),
        ("SspaiHandler", True),
        ("AppinnHandler", True),
    ]

    for u, (name, shared) in zip(urls, expected):
        h = get_handler_for_url(u)
        assert h is not None
        assert h.handler_name == name
        assert should_use_shared_browser_for_url(u) is shared
