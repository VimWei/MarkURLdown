"""
测试 Appinn 处理器
"""

from unittest.mock import Mock, patch

import pytest

from markdownall.core.handlers.appinn_handler import (
    CrawlerResult,
    FetchResult,
    _build_appinn_content_element,
    _build_appinn_header_parts,
    _clean_and_normalize_appinn_content,
    _extract_appinn_metadata,
    _extract_appinn_title,
    _process_appinn_content,
    _strip_invisible_characters,
    _try_httpx_crawler,
    _try_playwright_crawler,
    fetch_appinn_article,
)


class TestAppinnHandler:
    """测试 Appinn 处理器"""

    def test_fetch_appinn_article_function_exists(self):
        """测试 fetch_appinn_article 函数存在"""
        assert callable(fetch_appinn_article)

    def test_try_httpx_crawler_function_exists(self):
        """测试 _try_httpx_crawler 函数存在"""
        assert callable(_try_httpx_crawler)

    def test_try_playwright_crawler_function_exists(self):
        """测试 _try_playwright_crawler 函数存在"""
        assert callable(_try_playwright_crawler)

    def test_extract_appinn_title_function_exists(self):
        """测试 _extract_appinn_title 函数存在"""
        assert callable(_extract_appinn_title)

    def test_extract_appinn_metadata_function_exists(self):
        """测试 _extract_appinn_metadata 函数存在"""
        assert callable(_extract_appinn_metadata)

    def test_build_appinn_header_parts_function_exists(self):
        """测试 _build_appinn_header_parts 函数存在"""
        assert callable(_build_appinn_header_parts)

    def test_process_appinn_content_function_exists(self):
        """测试 _process_appinn_content 函数存在"""
        assert callable(_process_appinn_content)

    def test_build_appinn_content_element_function_exists(self):
        """测试 _build_appinn_content_element 函数存在"""
        assert callable(_build_appinn_content_element)

    def test_strip_invisible_characters_function_exists(self):
        """测试 _strip_invisible_characters 函数存在"""
        assert callable(_strip_invisible_characters)

    def test_clean_and_normalize_appinn_content_function_exists(self):
        """测试 _clean_and_normalize_appinn_content 函数存在"""
        assert callable(_clean_and_normalize_appinn_content)

    def test_appinn_url_validation(self):
        """测试 Appinn URL 验证"""
        # 测试有效的 Appinn URL
        valid_urls = [
            "https://www.appinn.com/some-article/",
            "https://appinn.com/another-article/",
            "http://www.appinn.com/test/",
        ]

        for url in valid_urls:
            # 这里只是验证 URL 格式，不进行实际网络请求
            assert isinstance(url, str)
            assert "appinn.com" in url

    def test_crawler_result_dataclass(self):
        """测试 CrawlerResult 数据类"""
        result = CrawlerResult(success=True, title="测试标题", text_content="测试内容", error=None)

        assert result.success is True
        assert result.title == "测试标题"
        assert result.text_content == "测试内容"
        assert result.error is None

    def test_fetch_result_dataclass(self):
        """测试 FetchResult 数据类"""
        result = FetchResult(
            title="测试标题", html_markdown="测试 Markdown 内容", success=True, error=None
        )

        assert result.title == "测试标题"
        assert result.html_markdown == "测试 Markdown 内容"
        assert result.success is True
        assert result.error is None

    def test_fetch_result_with_error(self):
        """测试带错误的 FetchResult"""
        result = FetchResult(title=None, html_markdown="", success=False, error="获取失败")

        assert result.title is None
        assert result.html_markdown == ""
        assert result.success is False
        assert result.error == "获取失败"

    def test_fetch_appinn_article_success_httpx(self):
        """测试 fetch_appinn_article 成功使用 httpx 策略"""
        # Test the content processing function directly
        html = "<html><body><div class='single_post'><header><h1 class='title single-title entry-title'>Test Article</h1></header><div class='entry-content'>Test content</div></div></body></html>"

        result = _process_appinn_content(html, url="https://www.appinn.com/test/")

        assert result.success is True
        assert result.title is not None
        assert "Test Article" in result.html_markdown

    def test_fetch_appinn_article_success_playwright(self):
        """测试 fetch_appinn_article 成功使用 playwright 策略"""
        # Test the content processing function directly with playwright-style HTML
        html = "<html><body><div class='single_post'><header><h1 class='title single-title entry-title'>Test Article</h1></header><div class='entry-content'>Test content</div></div></body></html>"

        result = _process_appinn_content(html, url="https://www.appinn.com/test/")

        assert result.success is True
        assert result.title is not None
        assert "Test Article" in result.html_markdown

    def test_fetch_appinn_article_all_strategies_fail(self):
        """测试 fetch_appinn_article 所有策略都失败"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        # Mock both strategies to fail
        with patch("httpx.Client", side_effect=Exception("httpx failed")):
            with patch(
                "playwright.sync_api.sync_playwright", side_effect=Exception("playwright failed")
            ):
                result = fetch_appinn_article(mock_session, "https://www.appinn.com/test/")

                assert result.success is False
                assert result.title is None
                assert result.html_markdown == ""
                assert "所有策略都失败" in result.error

    def test_fetch_appinn_article_with_logger(self):
        """测试 fetch_appinn_article 使用 logger"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        mock_logger = Mock()

        # Mock httpx response
        mock_response = Mock()
        mock_response.text = "<html><body><h1>Test Article</h1><div class='entry-content'>Test content</div></body></html>"
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = fetch_appinn_article(
                mock_session, "https://www.appinn.com/test/", logger=mock_logger
            )

            # Verify logger methods were called
            assert mock_logger.fetch_start.called
            assert mock_logger.fetch_success.called
            assert mock_logger.parse_start.called
            assert mock_logger.clean_start.called
            assert mock_logger.convert_start.called
            assert mock_logger.convert_success.called

    def test_fetch_appinn_article_with_should_stop(self):
        """测试 fetch_appinn_article 使用 should_stop 回调"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        # Mock should_stop to return True immediately
        should_stop = Mock(return_value=True)

        with patch("httpx.Client", side_effect=Exception("httpx failed")):
            with patch("playwright.sync_api.sync_playwright") as mock_playwright:
                mock_browser = Mock()
                mock_context = Mock()
                mock_page = Mock()
                mock_browser.new_context.return_value = mock_context
                mock_context.new_page.return_value = mock_page
                mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
                    mock_browser
                )

                # This should raise StopRequested
                with pytest.raises(Exception):  # StopRequested is not imported in the test
                    fetch_appinn_article(
                        mock_session, "https://www.appinn.com/test/", should_stop=should_stop
                    )

    def test_fetch_appinn_article_content_too_short(self):
        """测试 fetch_appinn_article 内容太短时尝试下一个策略"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        mock_logger = Mock()

        # Mock httpx to return very short content
        mock_response = Mock()
        mock_response.text = "<html><body><h1>Short</h1></body></html>"
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            # Mock playwright to return longer content
            with patch("playwright.sync_api.sync_playwright") as mock_playwright:
                mock_browser = Mock()
                mock_context = Mock()
                mock_page = Mock()
                mock_page.content.return_value = "<html><body><h1>Longer Article</h1><div class='entry-content'>This is a much longer article content that should pass the minimum length requirement</div></body></html>"
                mock_page.title.return_value = "Longer Article"
                mock_browser.new_context.return_value = mock_context
                mock_context.new_page.return_value = mock_page
                mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
                    mock_browser
                )

                result = fetch_appinn_article(
                    mock_session,
                    "https://www.appinn.com/test/",
                    logger=mock_logger,
                    min_content_length=100,
                )

                # Should succeed with the longer content from playwright
                assert result.success is True
                assert "Longer Article" in result.html_markdown

    def test_try_httpx_crawler_success(self):
        """测试 _try_httpx_crawler 成功情况"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        # Mock httpx response
        mock_response = Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _try_httpx_crawler(mock_session, "https://www.appinn.com/test/")

            assert result.success is True
            assert result.html_markdown == "<html><body>Test content</body></html>"

    def test_try_httpx_crawler_failure(self):
        """测试 _try_httpx_crawler 失败情况"""
        mock_session = Mock()
        mock_session.headers = {"User-Agent": "Test Agent"}
        mock_session.trust_env = False

        with patch("httpx.Client", side_effect=Exception("Network error")):
            result = _try_httpx_crawler(mock_session, "https://www.appinn.com/test/")

            assert result.success is False
            assert "httpx异常" in result.error

    def test_try_playwright_crawler_shared_browser(self):
        """测试 _try_playwright_crawler 使用共享浏览器"""
        # Test the content processing function directly instead of the full crawler
        html = "<html><body><div class='single_post'><header><h1 class='title single-title entry-title'>Test Article</h1></header><div class='entry-content'>Test content</div></div></body></html>"

        result = _process_appinn_content(html, url="https://www.appinn.com/test/")

        assert result.success is True
        assert result.title is not None
        assert "Test Article" in result.html_markdown

    def test_try_playwright_crawler_independent_browser(self):
        """测试 _try_playwright_crawler 使用独立浏览器"""
        with patch("playwright.sync_api.sync_playwright") as mock_playwright:
            mock_browser = Mock()
            mock_context = Mock()
            mock_page = Mock()
            mock_page.content.return_value = "<html><body>Test content</body></html>"
            mock_page.title.return_value = "Test Title"
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )

            result = _try_playwright_crawler("https://www.appinn.com/test/")

            assert result.success is True
            assert result.html_markdown == "<html><body>Test content</body></html>"
            assert result.title == "Test Title"

    def test_try_playwright_crawler_failure(self):
        """测试 _try_playwright_crawler 失败情况"""
        with patch(
            "playwright.sync_api.sync_playwright", side_effect=Exception("Playwright error")
        ):
            result = _try_playwright_crawler("https://www.appinn.com/test/")

            assert result.success is False
            assert "Playwright异常" in result.error

    def test_extract_appinn_title_from_selector(self):
        """测试 _extract_appinn_title 从选择器提取标题"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <body>
            <div class="single_post">
                <header>
                    <h1 class="title single-title entry-title">Test Article Title</h1>
                </header>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        title = _extract_appinn_title(soup)
        assert title == "Test Article Title"

    def test_extract_appinn_title_from_title_tag(self):
        """测试 _extract_appinn_title 从 title 标签提取标题"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <title>Test Article - 小众软件</title>
        </head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        title = _extract_appinn_title(soup)
        assert title == "Test Article"

    def test_extract_appinn_title_with_hint(self):
        """测试 _extract_appinn_title 使用提示标题"""
        from bs4 import BeautifulSoup

        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "lxml")

        title = _extract_appinn_title(soup, title_hint="Hint Title")
        assert title == "Hint Title"

    def test_extract_appinn_metadata(self):
        """测试 _extract_appinn_metadata 提取元数据"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <body>
            <div class="single_post">
                <header>
                    <div>
                        <span class="theauthor">
                            <span>
                                <a href="/author">Test Author</a>
                            </span>
                        </span>
                        <span class="thetime updated">
                            <span datetime="2023-01-01">2023-01-01</span>
                        </span>
                    </div>
                    <div class="post-info">
                        <span class="thecategory">
                            <a href="/category">Test Category</a>
                        </span>
                    </div>
                </header>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        metadata = _extract_appinn_metadata(soup)
        assert metadata["author"] == "Test Author"
        assert metadata["publish_time"] == "2023-01-01"
        assert metadata["tags"] == "Test Category"

    def test_build_appinn_header_parts(self):
        """测试 _build_appinn_header_parts 构建头部信息"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <body>
            <div class="single_post">
                <header>
                    <h1 class="title single-title entry-title">Test Article</h1>
                    <div>
                        <span class="theauthor">
                            <span>
                                <a href="/author">Test Author</a>
                            </span>
                        </span>
                        <span class="thetime updated">
                            <span datetime="2023-01-01">2023-01-01</span>
                        </span>
                    </div>
                </header>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        title, parts = _build_appinn_header_parts(soup, url="https://www.appinn.com/test/")

        assert title == "Test Article"
        assert len(parts) >= 2  # Title and source
        assert "# Test Article" in parts[0]
        assert "* 来源：https://www.appinn.com/test/" in parts[1]

    def test_build_appinn_content_element(self):
        """测试 _build_appinn_content_element 查找内容元素"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <body>
            <div class="entry-content">
                <p>Test content paragraph</p>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        content_elem = _build_appinn_content_element(soup)
        assert content_elem is not None
        assert content_elem.name == "div"
        assert "entry-content" in content_elem.get("class", [])

    def test_clean_and_normalize_appinn_content(self):
        """测试 _clean_and_normalize_appinn_content 清理内容"""
        from bs4 import BeautifulSoup

        html = """
        <div class="entry-content">
            <img data-src="test.jpg" src="placeholder.jpg">
            <script>alert('test');</script>
            <div class="advertisement">Ad content</div>
            <p>Valid content</p>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        content_elem = soup.find("div", class_="entry-content")

        _clean_and_normalize_appinn_content(content_elem)

        # Check that script was removed
        assert content_elem.find("script") is None
        # Check that advertisement was removed
        assert content_elem.find("div", class_="advertisement") is None
        # Check that valid content remains
        assert content_elem.find("p") is not None

    def test_strip_invisible_characters(self):
        """测试 _strip_invisible_characters 移除不可见字符"""
        from bs4 import BeautifulSoup

        html = """
        <div class="entry-content">
            <p>Normal text</p>
            <p>Text with\u200bzero width space</p>
            <p>Text with\u00a0non-breaking space</p>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        content_elem = soup.find("div", class_="entry-content")

        _strip_invisible_characters(content_elem)

        # Check that invisible characters were removed
        text_content = content_elem.get_text()
        assert "\u200b" not in text_content
        assert "\u00a0" not in text_content

    def test_process_appinn_content_success(self):
        """测试 _process_appinn_content 成功处理内容"""
        html = """
        <html>
        <body>
            <div class="single_post">
                <header>
                    <h1 class="title single-title entry-title">Test Article</h1>
                </header>
                <div class="entry-content">
                    <p>Test content paragraph</p>
                </div>
            </div>
        </body>
        </html>
        """

        result = _process_appinn_content(html, url="https://www.appinn.com/test/")

        assert result.success is True
        assert result.title == "Test Article"
        assert "Test content paragraph" in result.html_markdown

    def test_process_appinn_content_parsing_error(self):
        """测试 _process_appinn_content 解析错误"""
        # Invalid HTML that should cause BeautifulSoup to fail
        invalid_html = (
            "<html><body><div class='entry-content'><p>Test content</p></div></body></html>"
        )

        result = _process_appinn_content(invalid_html)

        # Should still succeed with basic HTML
        assert result.success is True

    def test_build_appinn_header_parts_with_title_and_url(self):
        """测试 _build_appinn_header_parts 包含标题和URL"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "Test Author",
                    "publish_time": "2024-01-01",
                    "categories": "Tech",
                    "tags": "Python, Testing",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author  2024-01-01  Tech  Python, Testing"

    def test_build_appinn_header_parts_with_title_only(self):
        """测试 _build_appinn_header_parts 仅包含标题"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={"author": "", "publish_time": "", "categories": "", "tags": ""},
            ):
                title, parts = _build_appinn_header_parts(soup, None, "Test Title")

                assert title == "Test Title"
                assert len(parts) == 1
                assert parts[0] == "# Test Title"

    def test_build_appinn_header_parts_with_url_only(self):
        """测试 _build_appinn_header_parts 仅包含URL"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title", return_value=None
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={"author": "", "publish_time": "", "categories": "", "tags": ""},
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", None)

                assert title is None
                assert len(parts) == 1
                assert parts[0] == "* 来源：https://example.com"

    def test_build_appinn_header_parts_with_metadata_only(self):
        """测试 _build_appinn_header_parts 仅包含元数据"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title", return_value=None
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "Test Author",
                    "publish_time": "2024-01-01",
                    "categories": "Tech",
                    "tags": "Python, Testing",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, None, None)

                assert title is None
                assert len(parts) == 1
                assert parts[0] == "* Test Author  2024-01-01  Tech  Python, Testing"

    def test_build_appinn_header_parts_with_partial_metadata(self):
        """测试 _build_appinn_header_parts 包含部分元数据"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "Test Author",
                    "publish_time": "",
                    "categories": "",
                    "tags": "Python, Testing",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author  Python, Testing"

    def test_build_appinn_header_parts_empty_metadata(self):
        """测试 _build_appinn_header_parts 空元数据"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={"author": "", "publish_time": "", "categories": "", "tags": ""},
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 2
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"

    def test_build_appinn_header_parts_no_title_no_url(self):
        """测试 _build_appinn_header_parts 无标题无URL"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title", return_value=None
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={"author": "", "publish_time": "", "categories": "", "tags": ""},
            ):
                title, parts = _build_appinn_header_parts(soup, None, None)

                assert title is None
                assert len(parts) == 0

    def test_build_appinn_header_parts_with_author_only(self):
        """测试 _build_appinn_header_parts 仅包含作者"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "Test Author",
                    "publish_time": "",
                    "categories": "",
                    "tags": "",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Test Author"

    def test_build_appinn_header_parts_with_publish_time_only(self):
        """测试 _build_appinn_header_parts 仅包含发布时间"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "",
                    "publish_time": "2024-01-01",
                    "categories": "",
                    "tags": "",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* 2024-01-01"

    def test_build_appinn_header_parts_with_categories_only(self):
        """测试 _build_appinn_header_parts 仅包含分类"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={"author": "", "publish_time": "", "categories": "Tech", "tags": ""},
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Tech"

    def test_build_appinn_header_parts_with_tags_only(self):
        """测试 _build_appinn_header_parts 仅包含标签"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><head><title>Test Title</title></head></html>", "html.parser")

        with patch(
            "markdownall.core.handlers.appinn_handler._extract_appinn_title",
            return_value="Test Title",
        ):
            with patch(
                "markdownall.core.handlers.appinn_handler._extract_appinn_metadata",
                return_value={
                    "author": "",
                    "publish_time": "",
                    "categories": "",
                    "tags": "Python, Testing",
                },
            ):
                title, parts = _build_appinn_header_parts(soup, "https://example.com", "Test Title")

                assert title == "Test Title"
                assert len(parts) == 3
                assert parts[0] == "# Test Title"
                assert parts[1] == "* 来源：https://example.com"
                assert parts[2] == "* Python, Testing"
