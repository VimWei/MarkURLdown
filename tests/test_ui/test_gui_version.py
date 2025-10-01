"""测试GUI窗口标题版本信息功能"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from PySide6.QtWidgets import QApplication

from markurldown.ui.pyside.gui import PySideApp
from markurldown.version import get_app_title


@pytest.mark.unit
def test_gui_window_title_uses_version():
    """测试GUI窗口标题使用版本信息"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 验证窗口标题包含版本信息
            window_title = app.windowTitle()
            assert window_title.startswith("MarkURLdown v")
            assert "v" in window_title
            
            # 验证标题与get_app_title()函数返回一致
            expected_title = get_app_title()
            assert window_title == expected_title


@pytest.mark.unit
def test_gui_window_title_format():
    """测试GUI窗口标题格式"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 验证窗口标题格式
            window_title = app.windowTitle()
            
            # 应该以"MarkURLdown v"开头
            assert window_title.startswith("MarkURLdown v")
            
            # 应该包含版本号（数字和点）
            import re
            version_pattern = r"MarkURLdown v\d+\.\d+\.\d+"
            assert re.match(version_pattern, window_title) is not None


@pytest.mark.unit
def test_gui_window_title_consistency():
    """测试GUI窗口标题与版本模块的一致性"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 多次调用get_app_title()应该返回相同结果
            title1 = get_app_title()
            title2 = get_app_title()
            assert title1 == title2
            
            # GUI窗口标题应该与get_app_title()一致
            assert app.windowTitle() == title1


@pytest.mark.integration
def test_gui_startup_with_version_info():
    """集成测试：验证GUI启动时版本信息正确显示"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 验证应用启动后窗口标题正确设置
            assert app.windowTitle() is not None
            assert app.windowTitle() != ""
            
            # 验证标题包含应用名称和版本
            title = app.windowTitle()
            assert "MarkURLdown" in title
            assert "v" in title
            
            # 验证版本号格式正确
            import re
            version_match = re.search(r"v(\d+\.\d+\.\d+)", title)
            assert version_match is not None
            version = version_match.group(1)
            
            # 验证版本号是有效的数字格式
            parts = version.split(".")
            assert len(parts) == 3
            for part in parts:
                assert part.isdigit()


@pytest.mark.unit
def test_gui_window_title_with_mocked_version():
    """测试使用模拟版本号的GUI窗口标题"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 模拟版本号
            with mock.patch("markurldown.version.get_version", return_value="1.2.3"):
                with mock.patch("markurldown.version.get_version_display", return_value="v1.2.3"):
                    with mock.patch("markurldown.version.get_app_title", return_value="MarkURLdown v1.2.3"):
                        # 创建PySideApp实例
                        app = PySideApp(root_dir=temp_dir)
                        
                        # 验证窗口标题使用模拟的版本信息
                        assert app.windowTitle() == "MarkURLdown v1.2.3"


@pytest.mark.unit
def test_gui_window_title_retranslate():
    """测试GUI重新翻译时窗口标题保持不变"""
    # 创建临时目录作为root_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        # 模拟QApplication以避免GUI初始化问题
        with mock.patch("PySide6.QtWidgets.QApplication") as mock_app:
            mock_app.instance.return_value = None
            
            # 创建PySideApp实例
            app = PySideApp(root_dir=temp_dir)
            
            # 记录初始标题
            initial_title = app.windowTitle()
            
            # 调用重新翻译方法
            app._retranslate_ui()
            
            # 验证标题保持不变（因为现在使用get_app_title()而不是翻译键）
            assert app.windowTitle() == initial_title
            assert app.windowTitle().startswith("MarkURLdown v")
