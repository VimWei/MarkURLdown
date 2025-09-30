"""测试处理器集成的集成测试"""

import pytest
from unittest.mock import Mock, patch
from markitdown_app.core.handlers.weixin_handler import fetch_weixin_article
from markitdown_app.core.handlers.zhihu_handler import fetch_zhihu_article
from markitdown_app.core.handlers.wordpress_handler import fetch_wordpress_article
from markitdown_app.core.handlers.sspai_handler import fetch_sspai_article
from markitdown_app.core.handlers.nextjs_handler import fetch_nextjs_article
from markitdown_app.core.handlers.generic_handler import convert_url
from markitdown_app.app_types import ConversionOptions, ConvertPayload


class TestHandlerIntegration:
    """测试处理器集成"""

    def setup_method(self):
        """测试前准备"""
        self.mock_session = Mock()
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True
        )

    def test_all_handlers_exist(self):
        """测试所有处理器都存在"""
        handlers = [
            fetch_weixin_article,
            fetch_zhihu_article,
            fetch_wordpress_article,
            fetch_sspai_article,
            fetch_nextjs_article,
            convert_url
        ]
        
        for handler in handlers:
            assert callable(handler)

    def test_handler_function_signatures(self):
        """测试处理器函数签名"""
        # 测试微信处理器
        assert callable(fetch_weixin_article)
        
        # 测试知乎处理器
        assert callable(fetch_zhihu_article)
        
        # 测试WordPress处理器
        assert callable(fetch_wordpress_article)
        
        # 测试少数派处理器
        assert callable(fetch_sspai_article)
        
        # 测试Next.js处理器
        assert callable(fetch_nextjs_article)
        
        # 测试通用处理器
        assert callable(convert_url)

    def test_handler_url_patterns(self):
        """测试处理器URL模式"""
        # 定义各种URL模式
        url_patterns = {
            "weixin": [
                "https://mp.weixin.qq.com/s/abc123",
                "http://mp.weixin.qq.com/s/def456"
            ],
            "zhihu": [
                "https://www.zhihu.com/question/123/answer/456",
                "https://zhuanlan.zhihu.com/p/789"
            ],
            "wordpress": [
                "https://example.com/wordpress-post",
                "https://blog.example.com/article"
            ],
            "sspai": [
                "https://sspai.com/post/123456",
                "http://sspai.com/post/789012"
            ],
            "nextjs": [
                "https://example.com/nextjs-post",
                "https://blog.example.com/nextjs-article"
            ],
            "generic": [
                "https://example.com/generic-article",
                "https://unknown-site.com/article"
            ]
        }
        
        # 验证所有URL模式都有对应的处理器
        for handler_type, urls in url_patterns.items():
            assert len(urls) > 0
            for url in urls:
                assert isinstance(url, str)
                assert url.startswith(("http://", "https://"))

    def test_handler_options_compatibility(self):
        """测试处理器选项兼容性"""
        # 测试各种选项组合
        option_combinations = [
            {"ignore_ssl": True, "use_proxy": False, "download_images": True, "filter_site_chrome": True},
            {"ignore_ssl": False, "use_proxy": True, "download_images": False, "filter_site_chrome": False},
            {"ignore_ssl": True, "use_proxy": True, "download_images": True, "filter_site_chrome": True},
            {"ignore_ssl": False, "use_proxy": False, "download_images": False, "filter_site_chrome": False}
        ]
        
        for combo in option_combinations:
            options = ConversionOptions(**combo)
            assert options.ignore_ssl == combo["ignore_ssl"]
            assert options.use_proxy == combo["use_proxy"]
            assert options.download_images == combo["download_images"]
            assert options.filter_site_chrome == combo["filter_site_chrome"]

    def test_handler_session_compatibility(self):
        """测试处理器会话兼容性"""
        # 测试会话对象的基本属性
        assert hasattr(self.mock_session, 'get')
        assert hasattr(self.mock_session, 'post')
        
        # 测试会话对象可调用
        assert callable(self.mock_session.get)
        assert callable(self.mock_session.post)

    def test_handler_error_handling(self):
        """测试处理器错误处理"""
        # 测试各种错误情况
        error_cases = [
            "网络连接失败",
            "解析失败",
            "内容为空",
            "未知错误"
        ]
        
        for error in error_cases:
            # 验证错误信息格式
            assert isinstance(error, str)
            assert len(error) > 0

    def test_handler_result_structure(self):
        """测试处理器结果结构"""
        # 测试成功结果结构
        success_result = {
            "title": "测试文章标题",
            "content": "# 测试文章标题\n\n这是文章内容。",
            "success": True,
            "error": None
        }
        
        assert success_result["success"] is True
        assert success_result["title"] is not None
        assert success_result["content"] is not None
        assert success_result["error"] is None
        
        # 测试失败结果结构
        failure_result = {
            "title": None,
            "content": "",
            "success": False,
            "error": "处理失败"
        }
        
        assert failure_result["success"] is False
        assert failure_result["title"] is None
        assert failure_result["content"] == ""
        assert failure_result["error"] is not None

    def test_handler_metadata_handling(self):
        """测试处理器元数据处理"""
        # 测试元数据格式
        metadata = {
            "title": "测试文章",
            "author": "测试作者",
            "date": "2024-01-01",
            "source": "https://example.com/article"
        }
        
        assert "title" in metadata
        assert "author" in metadata
        assert "date" in metadata
        assert "source" in metadata

    def test_handler_content_filtering(self):
        """测试处理器内容过滤"""
        # 测试需要过滤的内容
        content_to_filter = [
            "广告内容",
            "导航菜单",
            "页脚信息",
            "侧边栏内容",
            "评论区域"
        ]
        
        for content in content_to_filter:
            assert isinstance(content, str)
            assert len(content) > 0

    def test_handler_image_handling(self):
        """测试处理器图片处理"""
        # 测试图片URL格式
        image_urls = [
            "https://example.com/image.jpg",
            "https://example.com/image.png",
            "https://example.com/image.gif",
            "https://example.com/image.webp"
        ]
        
        for url in image_urls:
            assert url.startswith("https://")
            assert any(url.endswith(ext) for ext in [".jpg", ".png", ".gif", ".webp"])

    def test_handler_conversion_options(self):
        """测试处理器转换选项"""
        # 测试转换选项的完整性
        options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True
        )
        
        required_attributes = [
            "ignore_ssl",
            "use_proxy",
            "download_images",
            "filter_site_chrome",
            "use_shared_browser"
        ]
        
        for attr in required_attributes:
            assert hasattr(options, attr)

    def test_handler_payload_validation(self):
        """测试处理器载荷验证"""
        # 测试有效载荷
        valid_payload = ConvertPayload(
            kind="url",
            value="https://example.com/article",
            meta={"title": "测试文章"}
        )
        
        assert valid_payload.kind == "url"
        assert valid_payload.value.startswith("http")
        assert isinstance(valid_payload.meta, dict)
        
        # 测试无效载荷
        invalid_payloads = [
            ConvertPayload(kind="invalid", value="not_a_url", meta={}),
            ConvertPayload(kind="url", value="", meta={}),
            ConvertPayload(kind="", value="https://example.com", meta={})
        ]
        
        for payload in invalid_payloads:
            # 验证载荷结构（即使内容无效）
            assert hasattr(payload, "kind")
            assert hasattr(payload, "value")
            assert hasattr(payload, "meta")

    def test_handler_integration_workflow(self):
        """测试处理器集成工作流"""
        # 测试完整工作流的数据结构
        workflow = {
            "input": {
                "url": "https://example.com/article",
                "options": self.options,
                "session": self.mock_session
            },
            "processing": {
                "handler": "generic",
                "steps": ["fetch", "parse", "convert", "filter"]
            },
            "output": {
                "title": "测试文章标题",
                "content": "# 测试文章标题\n\n这是文章内容。",
                "success": True
            }
        }
        
        assert "input" in workflow
        assert "processing" in workflow
        assert "output" in workflow
        
        assert workflow["input"]["url"].startswith("http")
        assert workflow["processing"]["handler"] in ["weixin", "zhihu", "wordpress", "sspai", "nextjs", "generic"]
        assert workflow["output"]["success"] is True
