"""端到端集成测试"""

import pytest
from unittest.mock import Mock, patch
from markitdown_app.services.convert_service import ConvertService
from markitdown_app.app_types import SourceRequest, ConversionOptions


class TestEndToEnd:
    """端到端集成测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = ConvertService()
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True
        )

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        assert not self.service._should_stop
        assert self.service._thread is None

    def test_service_stop_functionality(self):
        """测试服务停止功能"""
        self.service.stop()
        assert self.service._should_stop is True

    def test_run_method_interface(self):
        """测试 run 方法接口"""
        # 验证 run 方法接受正确的参数
        requests_list = [SourceRequest(kind="url", value="https://example.com")]
        out_dir = "/tmp/test"
        
        # 验证方法存在且可调用
        assert hasattr(self.service, 'run')
        assert callable(self.service.run)
        
        # 验证方法签名（不实际调用，因为会启动线程）
        import inspect
        sig = inspect.signature(self.service.run)
        params = list(sig.parameters.keys())
        expected_params = ['requests_list', 'out_dir', 'options', 'on_event', 'signals']
        
        # 检查是否包含预期的参数
        for param in expected_params:
            assert param in params

    def test_event_callback_interface(self):
        """测试事件回调接口"""
        # 验证 _emit_event_safe 方法存在
        assert hasattr(self.service, '_emit_event_safe')
        assert callable(self.service._emit_event_safe)
        
        # 验证方法签名
        import inspect
        sig = inspect.signature(self.service._emit_event_safe)
        params = list(sig.parameters.keys())
        expected_params = ['event', 'on_event']
        
        for param in expected_params:
            assert param in params
