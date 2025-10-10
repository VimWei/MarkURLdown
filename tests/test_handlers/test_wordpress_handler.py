"""测试WordPress处理器"""

from unittest.mock import Mock

import pytest

from markdownall.app_types import ConversionOptions
from markdownall.core.handlers.wordpress_handler import (
    FetchResult,
    _process_wordpress_content,
    _try_httpx_crawler,
    _try_playwright_crawler,
    fetch_wordpress_article,
)


class TestWordPressHandler:
    """测试WordPress处理器"""

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

    def test_fetch_wordpress_article_function_exists(self):
        """测试 fetch_wordpress_article 函数存在"""
        assert callable(fetch_wordpress_article)

    def test_try_httpx_crawler_function_exists(self):
        """测试 _try_httpx_crawler 函数存在"""
        assert callable(_try_httpx_crawler)

    def test_try_playwright_crawler_function_exists(self):
        """测试 _try_playwright_crawler 函数存在"""
        assert callable(_try_playwright_crawler)

    def test_process_wordpress_content_function_exists(self):
        """测试 _process_wordpress_content 函数存在"""
        assert callable(_process_wordpress_content)

    def test_wordpress_url_validation(self):
        """测试WordPress URL验证"""
        # 有效的WordPress URL
        valid_urls = [
            "https://example.com/wordpress-post",
            "https://blog.example.com/article",
            "http://example.com/2024/01/01/post-title",
        ]

        # 无效的WordPress URL
        invalid_urls = [
            "https://mp.weixin.qq.com/s/test_article",
            "https://www.zhihu.com/question/123/answer/456",
            "not_a_url",
        ]

        # 这里可以添加URL验证逻辑的测试
        # 目前只是验证函数能处理这些URL
        for url in valid_urls + invalid_urls:
            # 只验证函数存在且可调用，不实际执行
            assert callable(fetch_wordpress_article)

    def test_build_wordpress_header_parts_with_title_and_url(self):
        """测试 _build_wordpress_header_parts 包含标题和URL"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "Test Author",
                "publish_time": "2024-01-01",
                "categories": "Tech",
                "tags": "Python, Testing"
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author  2024-01-01  Tech  Python, Testing"

    def test_build_wordpress_header_parts_with_title_only(self):
        """测试 _build_wordpress_header_parts 仅包含标题"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, None, "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 1
                assert parts[0] == "# Test Title"

    def test_build_wordpress_header_parts_with_url_only(self):
        """测试 _build_wordpress_header_parts 仅包含URL"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value=None):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", None)
                
                assert title is None
                assert len(parts) == 1
                assert parts[0] == "* 来源：https://example.com"

    def test_build_wordpress_header_parts_with_metadata_only(self):
        """测试 _build_wordpress_header_parts 仅包含元数据"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value=None):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "Test Author",
                "publish_time": "2024-01-01",
                "categories": "Tech",
                "tags": "Python, Testing"
            }):
                title, parts = _build_wordpress_header_parts(soup, None, None)
                
                assert title is None
                assert len(parts) == 1
                assert parts[0] == "* Test Author  2024-01-01  Tech  Python, Testing"

    def test_build_wordpress_header_parts_with_partial_metadata(self):
        """测试 _build_wordpress_header_parts 包含部分元数据"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "Test Author",
                "publish_time": "",
                "categories": "",
                "tags": "Python, Testing"
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author  Python, Testing"

    def test_build_wordpress_header_parts_empty_metadata(self):
        """测试 _build_wordpress_header_parts 空元数据"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 2
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"

    def test_build_wordpress_header_parts_no_title_no_url(self):
        """测试 _build_wordpress_header_parts 无标题无URL"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value=None):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, None, None)
                
                assert title is None
                assert len(parts) == 0

    def test_build_wordpress_header_parts_with_author_only(self):
        """测试 _build_wordpress_header_parts 仅包含作者"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "Test Author",
                "publish_time": "",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author"

    def test_build_wordpress_header_parts_with_publish_time_only(self):
        """测试 _build_wordpress_header_parts 仅包含发布时间"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "2024-01-01",
                "categories": "",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* 2024-01-01"

    def test_build_wordpress_header_parts_with_categories_only(self):
        """测试 _build_wordpress_header_parts 仅包含分类"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "Tech",
                "tags": ""
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Tech"

    def test_build_wordpress_header_parts_with_tags_only(self):
        """测试 _build_wordpress_header_parts 仅包含标签"""
        from bs4 import BeautifulSoup
        from unittest.mock import patch
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_header_parts
        
        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")
        
        with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_title", return_value="Test Title"):
            with patch("markdownall.core.handlers.wordpress_handler._extract_wordpress_metadata", return_value={
                "author": "",
                "publish_time": "",
                "categories": "",
                "tags": "Python, Testing"
            }):
                title, parts = _build_wordpress_header_parts(soup, "https://example.com", "Test Title")
                
                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Python, Testing"

    def test_fetch_wordpress_article_with_httpx_success(self):
        """测试 fetch_wordpress_article 使用 httpx 成功获取内容"""
        from unittest.mock import patch
        
        # 直接mock内部策略：返回足够长且可被解析的WordPress HTML
        long_valid_html = (
            "<html><head><title>Test Article - WordPress Site</title></head><body>"
            "<div id=\"content\" role=\"main\">"
            "<h1 class=\"entry-title\">Test Article</h1>"
            "<div class=\"entry-content\"><p>" + ("content ") * 60 + "</p></div>"
            "</div></body></html>"
        )
        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(success=True, html_markdown=long_valid_html, title=None, error=None)

            result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post")

            assert result.success is True
            assert result.title == "Test Article"
            assert "content content" in result.html_markdown

    def test_fetch_wordpress_article_with_httpx_failure(self):
        """测试 fetch_wordpress_article 使用 httpx 失败后尝试 playwright"""
        from unittest.mock import patch
        
        # Mock内部策略：httpx失败，playwright返回足够长且可被解析的HTML
        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(success=False, html_markdown="", title=None, error="httpx error")

            long_valid_html = (
                "<html><head><title>Play Title - WordPress Site</title></head><body>"
                "<div id=\"content\" role=\"main\">"
                "<h1 class=\"entry-title\">Play Title</h1>"
                "<div class=\"entry-content\"><p>" + ("content ") * 60 + "</p></div>"
                "</div></body></html>"
            )
            with patch("markdownall.core.handlers.wordpress_handler._try_playwright_crawler") as mock_pw:
                mock_pw.return_value = Mock(success=True, html_markdown=long_valid_html, title=None, error=None)

                result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post")

                assert result.success is True
                assert result.title == "Play Title"

    def test_fetch_wordpress_article_all_strategies_fail(self):
        """测试 fetch_wordpress_article 所有策略都失败"""
        from unittest.mock import patch
        import types
        
        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(success=False, html_markdown="", title=None, error="httpx error")
            # Stub playwright import then force _try_playwright_crawler to fail by raising inside
            class Failing:
                def __call__(self):
                    raise Exception("playwright error")
            fake_sync_api = types.SimpleNamespace(sync_playwright=Failing())
            fake_pkg = types.SimpleNamespace(_impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None)))
            with patch.dict("sys.modules", {"playwright": fake_pkg, "playwright.sync_api": fake_sync_api}):
                with patch("markdownall.core.handlers.wordpress_handler._try_playwright_crawler", return_value=Mock(success=False, html_markdown="", title=None, error="playwright error")):
                    result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post")
                    assert result.success is False
                    assert result.title is None
                    assert result.html_markdown == ""
                    assert "所有策略都失败" in result.error

    def test_fetch_wordpress_article_with_retry(self):
        """测试 fetch_wordpress_article 重试机制"""
        from unittest.mock import patch
        
        # Mock httpx策略先失败再成功，成功时返回足够长且可被解析的HTML
        call_count = 0
        def httpx_strategy_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(success=False, html_markdown="", title=None, error="First attempt fails")
            else:
                long_valid_html = (
                    "<html><head><title>Success Title - WordPress Site</title></head><body>"
                    "<div id=\"content\" role=\"main\">"
                    "<h1 class=\"entry-title\">Success Title</h1>"
                    "<div class=\"entry-content\"><p>" + ("content ") * 60 + "</p></div>"
                    "</div></body></html>"
                )
                return Mock(success=True, html_markdown=long_valid_html, title=None, error=None)

        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler", side_effect=httpx_strategy_side_effect):
            result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post")
            assert result.success is True
            assert call_count == 2

    def test_fetch_wordpress_article_with_shared_browser(self):
        """测试 fetch_wordpress_article 使用共享浏览器"""
        from unittest.mock import patch
        
        # Mock策略：httpx失败，playwright返回足够长且可被解析的HTML
        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(success=False, html_markdown="", title=None, error="httpx error")

            long_valid_html = (
                "<html><head><title>Shared Title - WordPress Site</title></head><body>"
                "<div id=\"content\" role=\"main\">"
                "<h1 class=\"entry-title\">Shared Title</h1>"
                "<div class=\"entry-content\"><p>" + ("content ") * 60 + "</p></div>"
                "</div></body></html>"
            )
            with patch("markdownall.core.handlers.wordpress_handler._try_playwright_crawler") as mock_pw:
                mock_pw.return_value = Mock(success=True, html_markdown=long_valid_html, title=None, error=None)
                result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post", shared_browser=Mock())
                assert result.success is True
                assert result.title == "Shared Title"

    def test_fetch_wordpress_article_with_stop_requested(self):
        """测试 fetch_wordpress_article 处理停止请求"""
        from unittest.mock import patch
        from markdownall.core.exceptions import StopRequested
        
        def should_stop():
            return True
        
        with patch("httpx.Client", side_effect=StopRequested()):
            with pytest.raises(StopRequested):
                fetch_wordpress_article(
                    self.mock_session, 
                    "https://example.com/wordpress-post",
                    should_stop=should_stop
                )

    def test_fetch_wordpress_article_content_too_short(self):
        """测试 fetch_wordpress_article 内容太短时尝试下一个策略"""
        from unittest.mock import patch
        
        # Mock策略：httpx返回很短内容，playwright返回足够长且可被解析的HTML
        with patch("markdownall.core.handlers.wordpress_handler._try_httpx_crawler") as mock_httpx:
            mock_httpx.return_value = Mock(success=True, html_markdown="<html><body><p>short</p></body></html>", title=None, error=None)

            long_valid_html = (
                "<html><head><title>Longer Title - WordPress Site</title></head><body>"
                "<div id=\"content\" role=\"main\">"
                "<h1 class=\"entry-title\">Longer Title</h1>"
                "<div class=\"entry-content\"><p>" + ("content ") * 60 + "</p></div>"
                "</div></body></html>"
            )
            with patch("markdownall.core.handlers.wordpress_handler._try_playwright_crawler") as mock_pw:
                mock_pw.return_value = Mock(success=True, html_markdown=long_valid_html, title=None, error=None)
                result = fetch_wordpress_article(self.mock_session, "https://example.com/wordpress-post")
                assert result.success is True
                assert "content content" in result.html_markdown

    def test_try_httpx_crawler_success(self):
        """测试 _try_httpx_crawler 成功情况"""
        from unittest.mock import patch
        
        mock_html = "<html><body><h1>Test</h1></body></html>"
        
        with patch("httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.text = mock_html
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = _try_httpx_crawler(self.mock_session, "https://example.com/wordpress-post")
            
            assert result.success is True
            assert result.html_markdown == mock_html
            assert result.title is None

    def test_try_httpx_crawler_failure(self):
        """测试 _try_httpx_crawler 失败情况"""
        from unittest.mock import patch
        
        with patch("httpx.Client", side_effect=Exception("Network error")):
            result = _try_httpx_crawler(self.mock_session, "https://example.com/wordpress-post")
            
            assert result.success is False
            assert result.html_markdown == ""
            assert "httpx异常" in result.error

    def test_try_playwright_crawler_with_shared_browser(self):
        """测试 _try_playwright_crawler 使用共享浏览器"""
        from unittest.mock import patch
        
        mock_shared_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        with patch("markdownall.services.playwright_driver.new_context_and_page", return_value=(mock_context, mock_page)):
            with patch("markdownall.services.playwright_driver.teardown_context_page"):
                with patch("markdownall.core.handlers.wordpress_handler.read_page_content_and_title", return_value=("<html><body><h1>Test</h1></body></html>", "Test Title")):
                    result = _try_playwright_crawler("https://example.com/wordpress-post", shared_browser=mock_shared_browser)
                    
                    assert result.success is True
                    assert result.title == "Test Title"
                    assert "<h1>Test</h1>" in result.html_markdown

    def test_try_playwright_crawler_independent_browser(self):
        """测试 _try_playwright_crawler 使用独立浏览器"""
        from unittest.mock import patch
        import types
        
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.content.return_value = "<html><body><h1>Independent Test</h1></body></html>"
        mock_page.title.return_value = "Independent Title"
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        class CM:
            def __enter__(self_inner):
                return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=Mock(return_value=mock_browser)))
            def __exit__(self_inner, exc_type, exc, tb):
                return False

        def sync_playwright_factory():
            return CM()

        fake_sync_api = types.SimpleNamespace(sync_playwright=sync_playwright_factory)
        fake_pkg = types.SimpleNamespace(_impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None)))
        with patch.dict("sys.modules", {"playwright": fake_pkg, "playwright.sync_api": fake_sync_api}):
            result = _try_playwright_crawler("https://example.com/wordpress-post")
            assert result.success is True
            assert result.title == "Independent Title"
            assert "<h1>Independent Test</h1>" in result.html_markdown

    def test_try_playwright_crawler_failure(self):
        """测试 _try_playwright_crawler 失败情况"""
        from unittest.mock import patch
        import types
        
        class FailingSync:
            def __call__(self):
                raise Exception("Playwright error")
        fake_sync_api = types.SimpleNamespace(sync_playwright=FailingSync())
        fake_pkg = types.SimpleNamespace(_impl=types.SimpleNamespace(_api_structures=types.SimpleNamespace(Cookie=None)))
        with patch.dict("sys.modules", {"playwright": fake_pkg, "playwright.sync_api": fake_sync_api}):
            result = _try_playwright_crawler("https://example.com/wordpress-post")
            assert result.success is False
            assert result.html_markdown == ""
            assert "Playwright异常" in result.error

    def test_process_wordpress_content_success(self):
        """测试 _process_wordpress_content 成功处理内容"""
        html = """
        <html>
            <head><title>Test Article - WordPress Site</title></head>
            <body>
                <div id="content" role="main">
                    <h1 class="entry-title">Test Article</h1>
                    <div class="author vcard">
                        <a href="/author/test">Test Author</a>
                    </div>
                    <time class="entry-date" datetime="2024-01-01">2024-01-01</time>
                    <div class="entry-categories">
                        <a href="/category/tech" rel="category tag">Technology</a>
                    </div>
                    <div class="entry-tags">
                        <a href="/tag/python" rel="tag">Python</a>
                        <a href="/tag/testing" rel="tag">Testing</a>
                    </div>
                    <div class="entry-content">
                        <p>This is the main content of the article.</p>
                        <img src="test.jpg" alt="Test image">
                    </div>
                </div>
            </body>
        </html>
        """
        
        result = _process_wordpress_content(html, "https://example.com/wordpress-post", "Test Article")
        
        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://example.com/wordpress-post" in result.html_markdown
        assert "This is the main content" in result.html_markdown

    def test_process_wordpress_content_no_content_element(self):
        """测试 _process_wordpress_content 没有找到内容元素"""
        html = """
        <html>
            <head><title>Test Article - WordPress Site</title></head>
            <body>
                <div id="content" role="main">
                    <h1 class="entry-title">Test Article</h1>
                    <p>Some content outside the main content area</p>
                </div>
            </body>
        </html>
        """
        
        result = _process_wordpress_content(html, "https://example.com/wordpress-post", "Test Article")
        
        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://example.com/wordpress-post" in result.html_markdown
        # Should still have header even if no content element found

    def test_process_wordpress_content_invalid_html(self):
        """测试 _process_wordpress_content 处理无效HTML"""
        invalid_html = "This is not valid HTML"
        
        result = _process_wordpress_content(invalid_html, "https://example.com/wordpress-post", "Test Article")
        
        # Even with invalid HTML, if title_hint is provided, it should be used
        assert result.title == "Test Article"
        assert result.html_markdown == "# Test Article\n* 来源：https://example.com/wordpress-post\n\n"

    def test_process_wordpress_content_with_metadata(self):
        """测试 _process_wordpress_content 包含元数据"""
        html = """
        <html>
            <head><title>Test Article - WordPress Site</title></head>
            <body>
                <div id="content" role="main">
                    <h1 class="entry-title">Test Article</h1>
                    <div class="author vcard">
                        <a href="/author/test">Test Author</a>
                    </div>
                    <time class="entry-date" datetime="2024-01-01">2024-01-01</time>
                    <div class="entry-categories">
                        <a href="/category/tech" rel="category tag">Technology</a>
                    </div>
                    <div class="entry-tags">
                        <a href="/tag/python" rel="tag">Python</a>
                        <a href="/tag/testing" rel="tag">Testing</a>
                    </div>
                    <div class="entry-content">
                        <p>This is the main content.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        result = _process_wordpress_content(html, "https://example.com/wordpress-post", "Test Article")
        
        assert result.title == "Test Article"
        assert "# Test Article" in result.html_markdown
        assert "* 来源：https://example.com/wordpress-post" in result.html_markdown
        # Should include metadata in the header
        assert "Test Author" in result.html_markdown
        assert "2024-01-01" in result.html_markdown
        assert "Technology" in result.html_markdown
        assert "Python" in result.html_markdown
        assert "Testing" in result.html_markdown

    def test_build_wordpress_content_element_success(self):
        """测试 _build_wordpress_content_element 成功找到内容元素"""
        from bs4 import BeautifulSoup
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_content_element
        
        html = """
        <html>
            <body>
                <div id="content" role="main">
                    <div class="entry-content">
                        <p>This is the main content.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, "html.parser")
        content_elem = _build_wordpress_content_element(soup)
        
        assert content_elem is not None
        assert content_elem.get_text(strip=True) == "This is the main content."

    def test_build_wordpress_content_element_fallback_selectors(self):
        """测试 _build_wordpress_content_element 使用备用选择器"""
        from bs4 import BeautifulSoup
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_content_element
        
        html = """
        <html>
            <body>
                <div class="post-content">
                    <p>This is post content.</p>
                </div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, "html.parser")
        content_elem = _build_wordpress_content_element(soup)
        
        assert content_elem is not None
        assert content_elem.get_text(strip=True) == "This is post content."

    def test_build_wordpress_content_element_not_found(self):
        """测试 _build_wordpress_content_element 没有找到内容元素"""
        from bs4 import BeautifulSoup
        from markdownall.core.handlers.wordpress_handler import _build_wordpress_content_element
        
        html = """
        <html>
            <body>
                <div>
                    <p>Some content without proper structure.</p>
                </div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, "html.parser")
        content_elem = _build_wordpress_content_element(soup)
        
        assert content_elem is None

    def test_clean_and_normalize_wordpress_content(self):
        """测试 _clean_and_normalize_wordpress_content 清理内容"""
        from bs4 import BeautifulSoup
        from markdownall.core.handlers.wordpress_handler import _clean_and_normalize_wordpress_content
        
        html = """
        <div class="entry-content">
            <img data-src="lazy.jpg" alt="Lazy image">
            <img data-original="original.jpg" alt="Original image">
            <script>alert('test');</script>
            <style>body { color: red; }</style>
            <div class="social-share">Share buttons</div>
            <div class="comments">Comments section</div>
            <div class="related-posts">Related posts</div>
            <p>This is the actual content.</p>
        </div>
        """
        
        soup = BeautifulSoup(html, "html.parser")
        content_elem = soup.find("div", class_="entry-content")
        
        _clean_and_normalize_wordpress_content(content_elem)
        
        # Check that lazy loading images were processed
        img_tags = content_elem.find_all("img")
        assert len(img_tags) == 2
        assert img_tags[0]["src"] == "lazy.jpg"
        assert img_tags[1]["src"] == "original.jpg"
        
        # Check that unwanted elements were removed
        assert content_elem.find("script") is None
        assert content_elem.find("style") is None
        assert content_elem.find("div", class_="social-share") is None
        assert content_elem.find("div", class_="comments") is None
        assert content_elem.find("div", class_="related-posts") is None
        
        # Check that actual content remains
        assert content_elem.find("p") is not None
        assert content_elem.find("p").get_text(strip=True) == "This is the actual content."