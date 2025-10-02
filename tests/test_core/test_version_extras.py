from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from unittest import mock

import pytest


def import_version_with(ver: str):
    path = Path(__file__).parent.parent.parent / "src" / "markdownall" / "version.py"
    spec = importlib.util.spec_from_file_location("markdownall.version_tested_extra", str(path))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    # Override getter directly on loaded module to control behavior
    mod.get_version = lambda: ver  # type: ignore[attr-defined]
    return mod


@pytest.mark.unit
def test_get_full_version_info_and_app_title():
    v = import_version_with("1.2.3")
    info = v.get_full_version_info()
    assert info["version"] == "1.2.3" and info["version_info"] == (1, 2, 3)
    assert v.get_app_title().startswith("MarkdownAll v")


@pytest.mark.unit
def test_get_app_title_format():
    """测试get_app_title函数返回格式"""
    v = import_version_with("2.1.0")
    title = v.get_app_title()

    # 验证格式：MarkdownAll v{version}
    assert title == "MarkdownAll v2.1.0"
    assert title.startswith("MarkdownAll v")

    # 验证版本号部分
    version_part = title.replace("MarkdownAll v", "")
    assert version_part == "2.1.0"


@pytest.mark.unit
def test_get_app_title_with_prerelease():
    """测试get_app_title函数处理预发布版本"""
    v = import_version_with("1.0.0a1")
    title = v.get_app_title()

    # 预发布版本也应该正确显示
    assert title == "MarkdownAll v1.0.0a1"
    assert "a1" in title


@pytest.mark.unit
def test_get_app_title_with_build_info():
    """测试get_app_title函数处理构建信息"""
    v = import_version_with("1.0.0+build.123")
    title = v.get_app_title()

    # 构建信息也应该包含在标题中
    assert title == "MarkdownAll v1.0.0+build.123"
    assert "build.123" in title


@pytest.mark.unit
def test_get_app_title_consistency():
    """测试get_app_title函数的一致性"""
    v = import_version_with("3.2.1")

    # 多次调用应该返回相同结果
    title1 = v.get_app_title()
    title2 = v.get_app_title()
    assert title1 == title2

    # 应该与get_version_display()相关
    display = v.get_version_display()
    expected_title = f"MarkdownAll {display}"
    assert title1 == expected_title


@pytest.mark.unit
def test_get_app_title_edge_cases():
    """测试get_app_title函数的边界情况"""
    # 测试零版本
    v = import_version_with("0.0.0")
    title = v.get_app_title()
    assert title == "MarkdownAll v0.0.0"

    # 测试大版本号
    v = import_version_with("999.999.999")
    title = v.get_app_title()
    assert title == "MarkdownAll v999.999.999"

    # 测试单数字版本
    v = import_version_with("1")
    title = v.get_app_title()
    assert title == "MarkdownAll v1"
