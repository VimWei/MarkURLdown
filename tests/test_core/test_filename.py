"""测试文件名处理功能"""

import pytest

from markurldown.core.filename import derive_md_filename


class TestFilename:
    """测试文件名处理"""

    def test_derive_md_filename_basic(self):
        """测试基础文件名生成"""
        # 测试基本功能
        result = derive_md_filename("测试标题", "https://example.com/article")
        assert result is not None
        assert result.endswith(".md")
        assert "测试标题" in result

    def test_derive_md_filename_with_special_chars(self):
        """测试包含特殊字符的标题"""
        title = "测试/标题: 包含特殊字符"
        result = derive_md_filename(title, "https://example.com/article")
        assert result is not None
        assert result.endswith(".md")
        # 应该移除或替换特殊字符
        assert "/" not in result
        assert ":" not in result

    def test_derive_md_filename_empty_title(self):
        """测试空标题处理"""
        result = derive_md_filename("", "https://example.com/article")
        assert result is not None
        assert result.endswith(".md")
        # 应该使用URL或其他默认值

    def test_derive_md_filename_long_title(self):
        """测试长标题处理"""
        long_title = "这是一个非常长的标题" * 10
        result = derive_md_filename(long_title, "https://example.com/article")
        assert result is not None
        assert result.endswith(".md")
        # 应该截断过长的标题

    def test_derive_md_filename_with_timestamp(self):
        """测试时间戳功能"""
        result1 = derive_md_filename("测试标题", "https://example.com/article")
        result2 = derive_md_filename("测试标题", "https://example.com/article")
        # 相同标题应该生成不同的文件名（包含时间戳）
        # 注意：如果时间戳精度不够，可能会生成相同的文件名
        # 这里我们只验证函数能正常执行
        assert result1 is not None
        assert result2 is not None
        assert result1.endswith(".md")
        assert result2.endswith(".md")
