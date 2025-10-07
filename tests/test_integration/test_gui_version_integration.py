"""集成测试：GUI版本信息显示功能"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# 不再使用 PySideApp；版本信息测试与窗口类无关
from markdownall.version import get_app_title, get_version


@pytest.mark.integration
def test_gui_version_integration_full_flow():
    """集成测试：完整的GUI版本信息显示流程"""
    # 测试版本信息的一致性，不实际创建GUI组件
    version_from_module = get_version()
    title_from_function = get_app_title()

    # 验证版本信息格式正确
    assert title_from_function.startswith("MarkdownAll v")
    assert version_from_module in title_from_function

    # 验证版本号格式正确
    import re

    version_match = re.search(r"v(\d+\.\d+\.\d+)", title_from_function)
    assert version_match is not None
    extracted_version = version_match.group(1)
    assert extracted_version == version_from_module

    # 验证版本号是有效的数字格式
    parts = extracted_version.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


@pytest.mark.integration
def test_gui_version_with_different_versions():
    """集成测试：使用不同版本号测试GUI版本信息"""
    test_versions = ["1.0.0", "2.1.3", "0.5.0", "10.20.30"]

    for version in test_versions:
        # 模拟特定版本号
        with mock.patch("markdownall.version.get_version", return_value=version):
            with mock.patch("markdownall.version.get_version_display", return_value=f"v{version}"):
                with mock.patch(
                    "markdownall.version.get_app_title", return_value=f"MarkdownAll v{version}"
                ):
                    # 验证版本信息正确显示
                    title = get_app_title()
                    assert title == f"MarkdownAll v{version}"
                    assert version in title


@pytest.mark.integration
def test_gui_version_consistency_across_operations():
    """集成测试：验证GUI操作过程中版本信息的一致性"""
    # 测试版本信息的一致性
    initial_title = get_app_title()

    # 多次调用应该返回相同结果
    title1 = get_app_title()
    title2 = get_app_title()
    assert title1 == title2
    assert title1 == initial_title

    # 验证标题格式正确
    assert initial_title.startswith("MarkdownAll v")

    # 验证版本号格式正确
    import re

    version_match = re.search(r"v(\d+\.\d+\.\d+)", initial_title)
    assert version_match is not None


@pytest.mark.integration
def test_gui_version_with_error_handling():
    """集成测试：版本信息获取失败时的错误处理"""
    # 模拟版本获取失败，返回默认版本
    with mock.patch("markdownall.version.get_version", return_value="0.0.0"):
        with mock.patch("markdownall.version.get_version_display", return_value="v0.0.0"):
            with mock.patch("markdownall.version.get_app_title", return_value="MarkdownAll v0.0.0"):
                # 验证即使版本获取失败，仍能正常显示
                title = get_app_title()
                assert title == "MarkdownAll v0.0.0"
                assert "MarkdownAll" in title


@pytest.mark.integration
def test_gui_version_with_prerelease_versions():
    """集成测试：预发布版本的GUI显示"""
    prerelease_versions = ["1.0.0a1", "2.1.0b2", "3.0.0rc1", "1.0.0-dev"]

    for version in prerelease_versions:
        # 模拟预发布版本
        with mock.patch("markdownall.version.get_version", return_value=version):
            with mock.patch("markdownall.version.get_version_display", return_value=f"v{version}"):
                with mock.patch(
                    "markdownall.version.get_app_title", return_value=f"MarkdownAll v{version}"
                ):
                    # 验证预发布版本正确显示
                    title = get_app_title()
                    assert title == f"MarkdownAll v{version}"
                    assert version in title

                    # 验证预发布标识符被正确包含
                    prerelease_indicators = ["a", "b", "rc", "dev"]
                    has_prerelease = any(
                        indicator in version for indicator in prerelease_indicators
                    )
                    if has_prerelease:
                        assert any(indicator in title for indicator in prerelease_indicators)
