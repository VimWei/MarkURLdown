from __future__ import annotations

import pytest

from markitdown_app.core.registry import (
    get_handler_for_url,
    should_use_shared_browser_for_url,
)


@pytest.mark.unit
def test_should_use_shared_browser_for_url_weixin_false():
    url = "https://mp.weixin.qq.com/s/abcdef"
    assert should_use_shared_browser_for_url(url) is False


@pytest.mark.unit
def test_should_use_shared_browser_for_url_zhihu_true():
    url = "https://zhuanlan.zhihu.com/p/123456"
    assert should_use_shared_browser_for_url(url) is True


@pytest.mark.unit
def test_get_handler_for_url_basic_mapping():
    cases = {
        "https://mp.weixin.qq.com/s/xyz": "WeixinHandler",
        "https://zhuanlan.zhihu.com/p/1": "ZhihuHandler",
        "https://skywind.me/blog/archives/100": "WordPressHandler",
        "https://guangzhengli.com/blog/hello": "NextJSHandler",
        "https://sspai.com/post/123": "SspaiHandler",
        "https://www.appinn.com/abcd": "AppinnHandler",
    }
    for url, expected_name in cases.items():
        handler = get_handler_for_url(url)
        assert handler is not None
        assert handler.handler_name == expected_name
