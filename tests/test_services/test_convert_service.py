"""测试转换服务"""

import pytest
from unittest.mock import Mock, patch
from markitdown_app.services.convert_service import ConvertService
from markitdown_app.app_types import SourceRequest, ConversionOptions, ProgressEvent


class TestConvertService:
    """测试转换服务"""

    def setup_method(self):
        """测试前准备"""
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True
        )
        self.service = ConvertService()

    def test_convert_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        # 检查初始状态
        assert not self.service._should_stop
        assert self.service._thread is None

    def test_convert_service_stop_flag(self):
        """测试停止标志功能"""
        # 测试设置停止标志
        self.service.stop()
        assert self.service._should_stop is True

    def test_run_method_exists(self):
        """测试 run 方法存在"""
        # 验证 run 方法存在且可调用
        assert hasattr(self.service, 'run')
        assert callable(self.service.run)

    def test_emit_event_safe_method_exists(self):
        """测试 _emit_event_safe 方法存在"""
        # 验证 _emit_event_safe 方法存在且可调用
        assert hasattr(self.service, '_emit_event_safe')
        assert callable(self.service._emit_event_safe)

    def test_worker_method_exists(self):
        """测试 _worker 方法存在"""
        # 验证 _worker 方法存在且可调用
        assert hasattr(self.service, '_worker')
        assert callable(self.service._worker)
