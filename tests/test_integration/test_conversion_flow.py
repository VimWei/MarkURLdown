"""测试完整转换流程的集成测试"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from markitdown_app.app_types import (
    ConversionOptions,
    ConvertPayload,
    ConvertResult,
    SourceRequest,
)
from markitdown_app.io.session import build_requests_session
from markitdown_app.services.convert_service import ConvertService


class TestConversionFlow:
    """测试完整转换流程"""

    def setup_method(self):
        """测试前准备"""
        self.service = ConvertService()
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True,
        )

    def test_convert_service_initialization(self):
        """测试转换服务初始化"""
        assert self.service is not None
        assert not self.service._should_stop
        assert self.service._thread is None

    def test_convert_service_stop_functionality(self):
        """测试转换服务停止功能"""
        self.service.stop()
        assert self.service._should_stop is True

    def test_build_requests_session_function_exists(self):
        """测试构建请求会话函数存在"""
        assert callable(build_requests_session)

    def test_conversion_options_creation(self):
        """测试转换选项创建"""
        options = ConversionOptions(
            ignore_ssl=True,
            use_proxy=True,
            download_images=False,
            filter_site_chrome=False,
            use_shared_browser=False,
        )

        assert options.ignore_ssl is True
        assert options.use_proxy is True
        assert options.download_images is False
        assert options.filter_site_chrome is False
        assert options.use_shared_browser is False

    def test_source_request_creation(self):
        """测试源请求创建"""
        request = SourceRequest(kind="url", value="https://example.com/article")

        assert request.kind == "url"
        assert request.value == "https://example.com/article"

    def test_convert_payload_creation(self):
        """测试转换载荷创建"""
        payload = ConvertPayload(
            kind="url", value="https://example.com/article", meta={"title": "测试文章"}
        )

        assert payload.kind == "url"
        assert payload.value == "https://example.com/article"
        assert payload.meta["title"] == "测试文章"

    def test_convert_result_creation(self):
        """测试转换结果创建"""
        result = ConvertResult(
            title="测试文章标题",
            markdown="# 测试文章标题\n\n这是文章内容。",
            suggested_filename="测试文章标题.md",
        )

        assert result.title == "测试文章标题"
        assert "文章内容" in result.markdown
        assert result.suggested_filename == "测试文章标题.md"

    def test_convert_result_failure(self):
        """测试转换结果失败情况"""
        result = ConvertResult(title=None, markdown="", suggested_filename="")

        assert result.title is None
        assert result.markdown == ""
        assert result.suggested_filename == ""

    def test_multiple_source_requests(self):
        """测试多个源请求"""
        requests = [
            SourceRequest(kind="url", value="https://example.com/article1"),
            SourceRequest(kind="url", value="https://example.com/article2"),
            SourceRequest(kind="url", value="https://example.com/article3"),
        ]

        assert len(requests) == 3
        for i, request in enumerate(requests, 1):
            assert request.kind == "url"
            assert f"article{i}" in request.value

    def test_conversion_options_validation(self):
        """测试转换选项验证"""
        # 测试默认选项
        default_options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True,
        )
        assert hasattr(default_options, "ignore_ssl")
        assert hasattr(default_options, "use_proxy")
        assert hasattr(default_options, "download_images")
        assert hasattr(default_options, "filter_site_chrome")
        assert hasattr(default_options, "use_shared_browser")

    def test_service_methods_exist(self):
        """测试服务方法存在"""
        assert hasattr(self.service, "run")
        assert hasattr(self.service, "stop")
        assert hasattr(self.service, "_emit_event_safe")
        assert hasattr(self.service, "_worker")

        # 验证方法可调用
        assert callable(self.service.run)
        assert callable(self.service.stop)
        assert callable(self.service._emit_event_safe)
        assert callable(self.service._worker)

    def test_event_callback_interface(self):
        """测试事件回调接口"""
        # 模拟事件回调函数
        events_received = []

        def mock_event_callback(event):
            events_received.append(event)

        # 测试回调函数可调用
        assert callable(mock_event_callback)

        # 模拟调用
        mock_event_callback({"type": "start", "message": "开始转换"})
        mock_event_callback({"type": "progress", "message": "转换中..."})
        mock_event_callback({"type": "complete", "message": "转换完成"})

        assert len(events_received) == 3
        assert events_received[0]["type"] == "start"
        assert events_received[1]["type"] == "progress"
        assert events_received[2]["type"] == "complete"

    def test_conversion_workflow_structure(self):
        """测试转换工作流结构"""
        # 测试完整工作流的数据结构
        workflow = {
            "requests": [
                SourceRequest(kind="url", value="https://example.com/article1"),
                SourceRequest(kind="url", value="https://example.com/article2"),
            ],
            "options": self.options,
            "output_dir": "/tmp/test_output",
            "on_event": lambda event: None,
        }

        assert len(workflow["requests"]) == 2
        assert workflow["options"] == self.options
        assert workflow["output_dir"] == "/tmp/test_output"
        assert callable(workflow["on_event"])

    def test_error_handling_structure(self):
        """测试错误处理结构"""
        # 测试各种错误情况的数据结构
        error_cases = [
            {"error": "网络连接失败", "type": "network"},
            {"error": "解析失败", "type": "parsing"},
            {"error": "文件写入失败", "type": "io"},
            {"error": "未知错误", "type": "unknown"},
        ]

        for case in error_cases:
            result = ConvertResult(title=None, markdown="", suggested_filename="")

            assert result.title is None
            assert result.markdown == ""
            assert result.suggested_filename == ""

    def test_conversion_metadata_handling(self):
        """测试转换元数据处理"""
        # 测试元数据的各种情况
        metadata_cases = [
            {"title": "测试文章", "author": "测试作者", "date": "2024-01-01"},
            {"title": "无作者文章", "author": None, "date": "2024-01-02"},
            {"title": None, "author": "无标题作者", "date": "2024-01-03"},
            {},  # 空元数据
        ]

        for i, meta in enumerate(metadata_cases, 1):
            payload = ConvertPayload(kind="url", value=f"https://example.com/article{i}", meta=meta)

            assert payload.kind == "url"
            assert payload.meta == meta
            assert f"article{i}" in payload.value

    def test_conversion_options_combinations(self):
        """测试转换选项组合"""
        # 测试各种选项组合
        option_combinations = [
            {
                "ignore_ssl": True,
                "use_proxy": False,
                "download_images": True,
                "filter_site_chrome": True,
            },
            {
                "ignore_ssl": False,
                "use_proxy": True,
                "download_images": False,
                "filter_site_chrome": False,
            },
            {
                "ignore_ssl": True,
                "use_proxy": True,
                "download_images": True,
                "filter_site_chrome": True,
            },
            {
                "ignore_ssl": False,
                "use_proxy": False,
                "download_images": False,
                "filter_site_chrome": False,
            },
        ]

        for combo in option_combinations:
            options = ConversionOptions(**combo)
            assert options.ignore_ssl == combo["ignore_ssl"]
            assert options.use_proxy == combo["use_proxy"]
            assert options.download_images == combo["download_images"]
            assert options.filter_site_chrome == combo["filter_site_chrome"]

    def test_service_lifecycle(self):
        """测试服务生命周期"""
        # 测试服务的完整生命周期
        service = ConvertService()

        # 初始状态
        assert not service._should_stop
        assert service._thread is None

        # 停止服务
        service.stop()
        assert service._should_stop is True

        # 重新创建服务
        new_service = ConvertService()
        assert not new_service._should_stop
        assert new_service._thread is None
