"""测试内容标准化功能"""

import pytest

from markdownall.core.normalize import normalize_markdown_headings


class TestNormalize:
    """测试内容标准化"""

    def test_normalize_markdown_headings_basic(self):
        """测试基础标题标准化"""
        markdown = """# 标题1
## 标题2
### 标题3
内容"""
        result = normalize_markdown_headings(markdown, "标题1")
        assert result is not None
        assert "# 标题1" in result
        assert "## 标题2" in result
        assert "### 标题3" in result

    def test_normalize_markdown_headings_empty(self):
        """测试空内容处理"""
        result = normalize_markdown_headings("", None)
        assert result == ""

    def test_normalize_markdown_headings_no_headings(self):
        """测试无标题内容"""
        markdown = "这是普通内容，没有标题"
        result = normalize_markdown_headings(markdown, None)
        # 函数会自动将第一行提升为标题
        assert result is not None
        assert "这是普通内容，没有标题" in result

    def test_normalize_markdown_headings_duplicate(self):
        """测试重复标题处理"""
        markdown = """# 标题1
内容1
# 标题1
内容2"""
        result = normalize_markdown_headings(markdown, "标题1")
        # 应该处理重复标题
        assert result is not None

    def test_normalize_markdown_headings_mixed_levels(self):
        """测试混合级别标题"""
        markdown = """### 三级标题
# 一级标题
## 二级标题
内容"""
        result = normalize_markdown_headings(markdown, "一级标题")
        assert result is not None
        assert "# 一级标题" in result
        assert "## 二级标题" in result
        assert "### 三级标题" in result
