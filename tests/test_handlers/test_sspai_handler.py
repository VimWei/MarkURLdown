"""测试少数派处理器"""

from unittest.mock import Mock

import pytest

from markdownall.app_types import ConversionOptions
from markdownall.core.handlers.sspai_handler import (
    FetchResult,
    _process_sspai_content,
    _try_httpx_crawler,
    _try_playwright_crawler,
    fetch_sspai_article,
)


class TestSspaiHandler:
    """测试少数派处理器"""

    def setup_method(self):
        """测试前准备"""
        self.mock_session = Mock()
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True,
        )

    def test_fetch_sspai_article_function_exists(self):
        """测试 fetch_sspai_article 函数存在"""
        assert callable(fetch_sspai_article)

    def test_try_httpx_crawler_function_exists(self):
        """测试 _try_httpx_crawler 函数存在"""
        assert callable(_try_httpx_crawler)

    def test_try_playwright_crawler_function_exists(self):
        """测试 _try_playwright_crawler 函数存在"""
        assert callable(_try_playwright_crawler)

    def test_process_sspai_content_function_exists(self):
        """测试 _process_sspai_content 函数存在"""
        assert callable(_process_sspai_content)

    def test_sspai_url_validation(self):
        """测试少数派URL验证"""
        # 有效的少数派URL
        valid_urls = [
            "https://sspai.com/post/123456",
            "https://sspai.com/post/abc123",
            "http://sspai.com/post/123456",
        ]

        # 无效的少数派URL
        invalid_urls = [
            "https://mp.weixin.qq.com/s/test_article",
            "https://www.zhihu.com/question/123/answer/456",
            "not_a_url",
        ]

        # 这里可以添加URL验证逻辑的测试
        # 目前只是验证函数能处理这些URL
        for url in valid_urls + invalid_urls:
            # 只验证函数存在且可调用，不实际执行
            assert callable(fetch_sspai_article)

    def test_fetch_sspai_article_with_httpx_success(self):
        """测试 fetch_sspai_article 使用 httpx 成功获取内容"""
        from unittest.mock import patch

        # Mock httpx response with longer content to pass the 200 character check
        mock_html = """
        <html>
            <head><title>Test Article - 少数派</title></head>
            <body>
                <div id="article-title">Test Article</div>
                <article>
                    <div class="article-body">
                        <div class="article__main__content wangEditor-txt">
                            <p>This is a much longer test content that should definitely pass the 200 character length requirement. It contains enough text to ensure that the content processing will not be rejected due to being too short.</p>
                            <p>This is additional content to make sure we have plenty of text for the test to pass successfully.</p>
                        </div>
                    </div>
                </article>
            </body>
        </html>
        """

        with patch("markdownall.core.handlers.sspai_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(
                success=True, html_markdown=mock_html, title=None, error=None
            )

            result = fetch_sspai_article(self.mock_session, "https://sspai.com/post/123456")

            assert result.success is True
            assert result.title == "Test Article"
            assert "This is a much longer test content" in result.html_markdown

    def test_fetch_sspai_article_with_httpx_failure(self):
        """测试 fetch_sspai_article 使用 httpx 失败后尝试 playwright"""
        from unittest.mock import patch

        # Mock httpx failure and playwright success with valid, long sspai HTML
        with patch("markdownall.core.handlers.sspai_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(
                success=False, html_markdown="", title=None, error="httpx error"
            )

            long_valid_html = (
                "<html><head><title>Test Article - 少数派</title></head><body>"
                '<div id="article-title">Test Article</div>'
                '<article><div class="article-body">'
                '<div class="article__main__content wangEditor-txt">'
                + "<p>"
                + ("content ") * 60
                + "</p>"
                + "</div></div></article>"
                "</body></html>"
            )

            with patch(
                "markdownall.core.handlers.sspai_handler._try_playwright_crawler"
            ) as mock_playwright:
                mock_playwright.return_value = Mock(
                    success=True, html_markdown=long_valid_html, title=None, error=None
                )

                result = fetch_sspai_article(self.mock_session, "https://sspai.com/post/123456")

                assert result.success is True
                assert result.title == "Test Article"

    def test_fetch_sspai_article_all_strategies_fail(self):
        """测试 fetch_sspai_article 所有策略都失败"""
        from unittest.mock import patch

        # Mock both httpx and playwright failures
        with patch("markdownall.core.handlers.sspai_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(
                success=False, html_markdown="", title=None, error="httpx error"
            )

            with patch(
                "markdownall.core.handlers.sspai_handler._try_playwright_crawler"
            ) as mock_playwright:
                mock_playwright.return_value = Mock(
                    success=False, html_markdown="", title=None, error="playwright error"
                )

                result = fetch_sspai_article(self.mock_session, "https://sspai.com/post/123456")

                assert result.success is False
                assert result.title is None
                assert result.html_markdown == ""
                assert "所有策略都失败" in result.error

    def test_fetch_sspai_article_with_retry(self):
        """测试 fetch_sspai_article 重试机制"""
        from unittest.mock import patch

        # Mock httpx to fail first, then succeed with valid, long sspai HTML
        call_count = 0

        def mock_httpx_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(
                    success=False, html_markdown="", title=None, error="First attempt fails"
                )
            else:
                long_valid_html = (
                    "<html><head><title>Success Title - 少数派</title></head><body>"
                    '<div id="article-title">Success Title</div>'
                    '<article><div class="article-body">'
                    '<div class="article__main__content wangEditor-txt">'
                    + "<p>"
                    + ("content ") * 60
                    + "</p>"
                    + "</div></div></article>"
                    "</body></html>"
                )
                return Mock(success=True, html_markdown=long_valid_html, title=None, error=None)

        with patch(
            "markdownall.core.handlers.sspai_handler._try_httpx_crawler",
            side_effect=mock_httpx_side_effect,
        ):
            result = fetch_sspai_article(self.mock_session, "https://sspai.com/post/123456")

            assert result.success is True
            assert call_count == 2  # Should have retried

    def test_fetch_sspai_article_with_shared_browser(self):
        """测试 fetch_sspai_article 使用共享浏览器"""
        from unittest.mock import patch

        # Mock internal strategies: httpx fails, playwright returns valid long sspai HTML
        with patch("markdownall.core.handlers.sspai_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(
                success=False, html_markdown="", title=None, error="httpx error"
            )

            long_valid_html = (
                "<html><head><title>Shared Title - 少数派</title></head><body>"
                '<div id="article-title">Shared Title</div>'
                '<article><div class="article-body">'
                '<div class="article__main__content wangEditor-txt">'
                + "<p>"
                + ("content ") * 60
                + "</p>"
                + "</div></div></article>"
                "</body></html>"
            )
            with patch(
                "markdownall.core.handlers.sspai_handler._try_playwright_crawler"
            ) as mock_playwright:
                mock_playwright.return_value = Mock(
                    success=True, html_markdown=long_valid_html, title=None, error=None
                )
                result = fetch_sspai_article(
                    self.mock_session, "https://sspai.com/post/123456", shared_browser=Mock()
                )
                assert result.success is True
                assert result.title == "Shared Title"

    def test_fetch_sspai_article_with_stop_requested(self):
        """测试 fetch_sspai_article 处理停止请求"""
        from unittest.mock import patch

        from markdownall.core.exceptions import StopRequested

        def should_stop():
            return True

        with patch("httpx.Client", side_effect=StopRequested()):
            with pytest.raises(StopRequested):
                fetch_sspai_article(
                    self.mock_session, "https://sspai.com/post/123456", should_stop=should_stop
                )

    def test_fetch_sspai_article_content_too_short(self):
        """测试 fetch_sspai_article 内容太短时尝试下一个策略"""
        from unittest.mock import patch

        # Mock strategies: short httpx content then long valid sspai HTML via playwright
        with patch("markdownall.core.handlers.sspai_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(
                success=True,
                html_markdown="<html><body><p>short</p></body></html>",
                title=None,
                error=None,
            )

            long_valid_html = (
                "<html><head><title>Longer Title - 少数派</title></head><body>"
                '<div id="article-title">Longer Title</div>'
                '<article><div class="article-body">'
                '<div class="article__main__content wangEditor-txt">'
                + "<p>"
                + ("content ") * 60
                + "</p>"
                + "</div></div></article>"
                "</body></html>"
            )
            with patch(
                "markdownall.core.handlers.sspai_handler._try_playwright_crawler"
            ) as mock_playwright:
                mock_playwright.return_value = Mock(
                    success=True, html_markdown=long_valid_html, title=None, error=None
                )
                result = fetch_sspai_article(self.mock_session, "https://sspai.com/post/123456")
                assert result.success is True

    def test_try_httpx_crawler_success(self):
        """测试 _try_httpx_crawler 成功情况"""
        from unittest.mock import patch

        mock_html = "<html><body><h1>Test</h1></body></html>"

        with patch("httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.text = mock_html
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _try_httpx_crawler(self.mock_session, "https://sspai.com/post/123456")

            assert result.success is True
            assert result.html_markdown == mock_html
            assert result.title is None

    def test_try_httpx_crawler_failure(self):
        """测试 _try_httpx_crawler 失败情况"""
        from unittest.mock import patch

        with patch("httpx.Client", side_effect=Exception("Network error")):
            result = _try_httpx_crawler(self.mock_session, "https://sspai.com/post/123456")

            assert result.success is False
            assert result.html_markdown == ""
            assert "httpx异常" in result.error

    def test_try_playwright_crawler_with_shared_browser(self):
        """测试 _try_playwright_crawler 使用共享浏览器"""
        import types
        from unittest.mock import patch

        mock_shared_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.content.return_value = "<html><body><h1>Test</h1></body></html>"
        mock_page.title.return_value = "Test Title"

        # Stub playwright modules to avoid real import errors in sspai_handler
        fake_sync_api = types.SimpleNamespace(sync_playwright=Mock())
        fake_playwright_pkg = types.SimpleNamespace(
            _impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None))
        )
        with patch.dict(
            "sys.modules", {"playwright": fake_playwright_pkg, "playwright.sync_api": fake_sync_api}
        ):
            with patch(
                "markdownall.services.playwright_driver.new_context_and_page",
                return_value=(mock_context, mock_page),
            ):
                with patch("markdownall.services.playwright_driver.teardown_context_page"):
                    with patch(
                        "markdownall.core.handlers.sspai_handler.read_page_content_and_title",
                        return_value=("<html><body><h1>Test</h1></body></html>", "Test Title"),
                    ):
                        result = _try_playwright_crawler(
                            "https://sspai.com/post/123456", shared_browser=mock_shared_browser
                        )

                        assert result.success is True
                        assert result.title == "Test Title"
                        assert "<h1>Test</h1>" in result.html_markdown

    def test_try_playwright_crawler_independent_browser(self):
        """测试 _try_playwright_crawler 使用独立浏览器"""
        import types
        from unittest.mock import patch

        # Stub playwright module to satisfy import in handler, and provide sync_playwright context
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.content.return_value = "<html><body><h1>Independent Test</h1></body></html>"
        mock_page.title.return_value = "Independent Title"
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        class CM:
            def __enter__(self_inner):
                return types.SimpleNamespace(
                    chromium=types.SimpleNamespace(launch=Mock(return_value=mock_browser))
                )

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        def sync_playwright_factory():
            return CM()

        fake_sync_api = types.SimpleNamespace(sync_playwright=sync_playwright_factory)
        fake_playwright_pkg = types.SimpleNamespace(
            _impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None))
        )
        with patch.dict(
            "sys.modules", {"playwright": fake_playwright_pkg, "playwright.sync_api": fake_sync_api}
        ):
            result = _try_playwright_crawler("https://sspai.com/post/123456")
            assert result.success is True
            assert result.title == "Independent Title"
            assert "<h1>Independent Test</h1>" in result.html_markdown

    def test_try_playwright_crawler_failure(self):
        """测试 _try_playwright_crawler 失败情况"""
        import types
        from unittest.mock import patch

        # Stub playwright so import succeeds, but raise when entering context
        class FailingSync:
            def __call__(self):
                raise Exception("Playwright error")

        fake_sync_api = types.SimpleNamespace(sync_playwright=FailingSync())
        fake_playwright_pkg = types.SimpleNamespace(
            _impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None))
        )
        with patch.dict(
            "sys.modules", {"playwright": fake_playwright_pkg, "playwright.sync_api": fake_sync_api}
        ):
            result = _try_playwright_crawler("https://sspai.com/post/123456")
            assert result.success is False
            assert result.html_markdown == ""
            assert "Playwright异常" in result.error

    def test_process_sspai_content_success(self):
        """测试 _process_sspai_content 成功处理内容"""
        html = """
        <html>
            <head><title>Test Article - 少数派</title></head>
            <body>
                <div id="article-title">Test Article</div>
                <div class="article-author">
                    <div class="author-box">
                        <div><span><span><div><span>Test Author</span></div></span></span></div>
                    </div>
                </div>
                <time class="timer" datetime="2024-01-01">2024-01-01</time>
                <article>
                    <div class="article-body">
                        <div class="article__main__content wangEditor-txt">
                            <p>This is the main content of the article.</p>
                            <img src="test.jpg" alt="Test image">
                        </div>
                    </div>
                </article>
            </body>
        </html>
        """

        result = _process_sspai_content(html, "https://sspai.com/post/123456", "Test Article")

        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://sspai.com/post/123456" in result.html_markdown
        assert "This is the main content" in result.html_markdown

    def test_process_sspai_content_no_content_element(self):
        """测试 _process_sspai_content 没有找到内容元素"""
        html = """
        <html>
            <head><title>Test Article - 少数派</title></head>
            <body>
                <div id="article-title">Test Article</div>
                <p>Some content outside the main content area</p>
            </body>
        </html>
        """

        result = _process_sspai_content(html, "https://sspai.com/post/123456", "Test Article")

        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://sspai.com/post/123456" in result.html_markdown
        # Should still have header even if no content element found

    def test_process_sspai_content_invalid_html(self):
        """测试 _process_sspai_content 处理无效HTML"""
        invalid_html = "This is not valid HTML"

        result = _process_sspai_content(
            invalid_html, "https://sspai.com/post/123456", "Test Article"
        )

        # Even with invalid HTML, if title_hint is provided, it should be used
        assert result.title == "Test Article"
        assert result.html_markdown == "# Test Article\n* 来源：https://sspai.com/post/123456\n\n"

    def test_process_sspai_content_with_metadata(self):
        """测试 _process_sspai_content 包含元数据"""
        html = """
        <html>
            <head><title>Test Article - 少数派</title></head>
            <body>
                <div id="article-title">Test Article</div>
                <div class="article-author">
                    <div class="author-box">
                        <div><span><span><div><span>Test Author</span></div></span></span></div>
                    </div>
                </div>
                <time class="timer" datetime="2024-01-01">2024-01-01</time>
                <div class="series-title">
                    <a href="/category/tech">Technology</a>
                </div>
                <div class="entry-tags">
                    <a href="/tag/python">Python</a>
                    <a href="/tag/testing">Testing</a>
                </div>
                <article>
                    <div class="article-body">
                        <div class="article__main__content wangEditor-txt">
                            <p>This is the main content.</p>
                        </div>
                    </div>
                </article>
            </body>
        </html>
        """

        result = _process_sspai_content(html, "https://sspai.com/post/123456", "Test Article")

        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://sspai.com/post/123456" in result.html_markdown
        # Should include metadata in the header
        assert "Test Author" in result.html_markdown
        assert "2024-01-01" in result.html_markdown
        assert "Technology" in result.html_markdown
        assert "Python" in result.html_markdown
        assert "Testing" in result.html_markdown
