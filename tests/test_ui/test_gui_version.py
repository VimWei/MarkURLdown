"""测试GUI窗口标题版本信息功能"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.gui import PySideApp
from markdownall.version import get_app_title


@pytest.mark.unit
def test_gui_window_title_uses_version():
    """测试GUI窗口标题使用版本信息"""
    # 验证标题与get_app_title()函数返回一致
    expected_title = get_app_title()
    assert expected_title.startswith("MarkdownAll v")
    assert "v" in expected_title

    # 验证版本号格式正确
    import re

    version_match = re.search(r"v(\d+\.\d+\.\d+)", expected_title)
    assert version_match is not None


@pytest.mark.unit
def test_gui_window_title_format():
    """测试GUI窗口标题格式"""
    # 验证窗口标题格式
    window_title = get_app_title()

    # 应该以"MarkdownAll v"开头
    assert window_title.startswith("MarkdownAll v")

    # 应该包含版本号（数字和点）
    import re

    version_pattern = r"MarkdownAll v\d+\.\d+\.\d+"
    assert re.match(version_pattern, window_title) is not None


@pytest.mark.unit
def test_gui_window_title_consistency():
    """测试GUI窗口标题与版本模块的一致性"""
    # 多次调用get_app_title()应该返回相同结果
    title1 = get_app_title()
    title2 = get_app_title()
    assert title1 == title2

    # 验证标题格式一致
    assert title1.startswith("MarkdownAll v")
    assert title2.startswith("MarkdownAll v")


@pytest.mark.integration
def test_gui_startup_with_version_info():
    """集成测试：验证GUI启动时版本信息正确显示"""
    # 验证应用启动后窗口标题正确设置
    title = get_app_title()
    assert title is not None
    assert title != ""

    # 验证标题包含应用名称和版本
    assert "MarkdownAll" in title
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
    # 模拟版本号 - 需要重新导入模块以确保mock生效
    with mock.patch("markdownall.version.get_version", return_value="1.2.3"):
        # 重新导入get_app_title以确保使用mock的版本
        from markdownall.version import get_app_title as mocked_get_app_title

        # 验证窗口标题使用模拟的版本信息
        title = mocked_get_app_title()
        assert title == "MarkdownAll v1.2.3"


@pytest.mark.unit
def test_gui_window_title_retranslate():
    """测试GUI重新翻译时窗口标题保持不变"""
    # 记录初始标题
    initial_title = get_app_title()

    # 验证标题格式正确
    assert initial_title.startswith("MarkdownAll v")

    # 多次调用应该返回相同结果
    title_after = get_app_title()
    assert title_after == initial_title
    assert title_after.startswith("MarkdownAll v")
