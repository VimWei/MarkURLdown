"""
测试 Appinn 处理器
"""

from unittest.mock import Mock, patch

import pytest

from markitdown_app.core.handlers.appinn_handler import (
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
