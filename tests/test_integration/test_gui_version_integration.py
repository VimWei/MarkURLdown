"""集成测试：GUI版本信息显示功能"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from markurldown.ui.pyside.gui import PySideApp
from markurldown.version import get_app_title, get_version


@pytest.mark.integration
def test_gui_version_integration_full_flow():
    """集成测试：完整的GUI版本信息显示流程"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 验证版本信息在整个流程中的一致性
            version_from_module = get_version()
            title_from_function = get_app_title()
            title_from_gui = app.windowTitle()
            
            # 所有版本信息应该一致
            assert title_from_function == title_from_gui
            assert title_from_function.startswith("MarkURLdown v")
            assert version_from_module in title_from_function
            
            # 验证版本号格式正确
            import re
            version_match = re.search(r"v(\d+\.\d+\.\d+)", title_from_gui)
            assert version_match is not None
            extracted_version = version_match.group(1)
            assert extracted_version == version_from_module


@pytest.mark.integration
def test_gui_version_with_different_versions():
    """集成测试：使用不同版本号测试GUI版本信息"""
    test_versions = ["1.0.0", "2.1.3", "0.5.0", "10.20.30"]
    
    for version in test_versions:
        # 创建临时目录作为root_dir
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟QApplication以避免GUI初始化问题
            with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
                mock_app.instance.return_value = None
                
                # 模拟特定版本号
                with mock.patch("markurldown.version.get_version", return_value=version):
                    with mock.patch("markurldown.version.get_version_display", return_value=f"v{version}"):
                        with mock.patch("markurldown.version.get_app_title", return_value=f"MarkURLdown v{version}"):
                            # 创建PySideApp实例
                            app = PySideApp(root_dir=temp_dir)
                            
                            # 验证版本信息正确显示
                            assert app.windowTitle() == f"MarkURLdown v{version}"
                            assert version in app.windowTitle()


@pytest.mark.integration
def test_gui_version_consistency_across_operations():
    """集成测试：验证GUI操作过程中版本信息的一致性"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 记录初始标题
            initial_title = app.windowTitle()
            
            # 模拟各种GUI操作
            # 1. 重新翻译UI
            app._retranslate_ui()
            assert app.windowTitle() == initial_title
            
            # 2. 模拟语言切换（如果有的话）
            # 这里可以添加更多GUI操作测试
            
            # 3. 验证标题在整个过程中保持一致
            final_title = app.windowTitle()
            assert final_title == initial_title
            assert final_title.startswith("MarkURLdown v")


@pytest.mark.integration
def test_gui_version_with_error_handling():
    """集成测试：版本信息获取失败时的错误处理"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 模拟版本获取失败，返回默认版本
            with mock.patch("markurldown.version.get_version", return_value="0.0.0"):
                with mock.patch("markurldown.version.get_version_display", return_value="v0.0.0"):
                    with mock.patch("markurldown.version.get_app_title", return_value="MarkURLdown v0.0.0"):
                        # 创建PySideApp实例
                        app = PySideApp(root_dir=temp_dir)
                        
                        # 验证即使版本获取失败，GUI仍能正常显示
                        assert app.windowTitle() == "MarkURLdown v0.0.0"
                        assert "MarkURLdown" in app.windowTitle()


@pytest.mark.integration
def test_gui_version_with_prerelease_versions():
    """集成测试：预发布版本的GUI显示"""
    prerelease_versions = ["1.0.0a1", "2.1.0b2", "3.0.0rc1", "1.0.0-dev"]
    
    for version in prerelease_versions:
        # 创建临时目录作为root_dir
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟QApplication以避免GUI初始化问题
            with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
                mock_app.instance.return_value = None
                
                # 模拟预发布版本
                with mock.patch("markurldown.version.get_version", return_value=version):
                    with mock.patch("markurldown.version.get_version_display", return_value=f"v{version}"):
                        with mock.patch("markurldown.version.get_app_title", return_value=f"MarkURLdown v{version}"):
                            # 创建PySideApp实例
                            app = PySideApp(root_dir=temp_dir)
                            
                            # 验证预发布版本正确显示
                            assert app.windowTitle() == f"MarkURLdown v{version}"
                            assert version in app.windowTitle()
                            
                            # 验证预发布标识符被正确包含
                            prerelease_indicators = ["a", "b", "rc", "dev"]
                            has_prerelease = any(indicator in version for indicator in prerelease_indicators)
                            if has_prerelease:
                                assert any(indicator in app.windowTitle() for indicator in prerelease_indicators)
