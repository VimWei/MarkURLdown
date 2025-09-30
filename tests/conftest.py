"""pytest 配置文件"""

from unittest.mock import Mock

import pytest

from markitdown_app.app_types import ConversionOptions


@pytest.fixture
def mock_session():
    """提供模拟的请求会话"""
    session = Mock()
    session.headers = {}
    session.cookies = {}
    return session


@pytest.fixture
def default_options():
    """提供默认的转换选项"""
    return ConversionOptions(
        ignore_ssl=False,
        use_proxy=False,
        download_images=True,
        filter_site_chrome=True,
        use_shared_browser=True,
    )


@pytest.fixture
def mock_weixin_url():
    """提供模拟的微信文章URL"""
    return "https://mp.weixin.qq.com/s/test_article_id"


@pytest.fixture
def mock_zhihu_url():
    """提供模拟的知乎文章URL"""
    return "https://zhuanlan.zhihu.com/p/test_article_id"


@pytest.fixture
def mock_generic_url():
    """提供模拟的通用网站URL"""
    return "https://example.com/article"


@pytest.fixture
def sample_html():
    """提供示例HTML内容"""
    return """
    <html>
        <head>
            <title>测试文章标题</title>
        </head>
        <body>
            <article>
                <h1>测试文章标题</h1>
                <p>这是测试文章的内容。</p>
                <img src="https://example.com/image.jpg" alt="测试图片">
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_markdown():
    """提供示例Markdown内容"""
    return """# 测试文章标题

这是测试文章的内容。

![测试图片](https://example.com/image.jpg)
"""


@pytest.fixture(autouse=True)
def setup_test_environment():
    """自动设置测试环境"""
    # 这里可以设置测试环境变量、清理临时文件等
    pass


def pytest_configure(config):
    """pytest 配置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "slow: 标记为慢速测试")
    config.addinivalue_line("markers", "integration: 标记为集成测试")
    config.addinivalue_line("markers", "unit: 标记为单元测试")
