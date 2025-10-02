"""测试通用处理器"""

from unittest.mock import Mock

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.handlers.generic_handler import convert_url


class TestGenericHandler:
    """测试通用处理器"""

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

    def test_convert_url_function_exists(self):
        """测试 convert_url 函数存在"""
        assert callable(convert_url)

    def test_convert_url_invalid_payload(self):
        """测试无效payload"""
        # 测试非URL类型的payload
        payload = ConvertPayload(kind="html", value="<html>content</html>", meta={})  # 错误的类型

        with pytest.raises(AssertionError):
            convert_url(payload, self.mock_session, self.options)

    def test_convert_url_valid_payload_structure(self):
        """测试有效payload结构"""
        payload = ConvertPayload(kind="url", value="https://example.com/article", meta={})

        # 验证payload结构正确
        assert payload.kind == "url"
        assert payload.value == "https://example.com/article"
        assert isinstance(payload.meta, dict)
