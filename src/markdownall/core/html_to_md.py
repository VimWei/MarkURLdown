from __future__ import annotations

import io
import re

from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo


def html_fragment_to_markdown(root) -> str:
    """
    使用 markitdown 将 HTML 片段转换为 Markdown

    Args:
        root: BeautifulSoup 元素或 HTML 字符串

    Returns:
        str: 转换后的 Markdown 文本
    """
    try:
        # 如果输入是 BeautifulSoup 元素，转换为字符串
        if hasattr(root, "__str__"):
            html_content = str(root)
        else:
            html_content = str(root)

        # 使用 HtmlConverter.convert_string 方法，可能更稳定
        from markitdown.converters._html_converter import HtmlConverter

        converter = HtmlConverter()
        result = converter.convert_string(html_content)
        return result.markdown

    except Exception as e:
        # 如果 markitdown 转换失败，回退到原来的实现
        print(f"markitdown 转换失败，回退到自定义转换器: {e}")
        return _legacy_html_fragment_to_markdown(root)


def _legacy_html_fragment_to_markdown(root) -> str:
    """原来的自定义转换实现，作为回退方案"""

    def node_to_md(node, in_heading: bool = False) -> str:
        if getattr(node, "name", None) is None:
            return str(node)

        name = node.name.lower()

        def children_md(sep: str = "", heading_context: bool = False) -> str:
            parts: list[str] = []
            for child in getattr(node, "children", []):
                part = node_to_md(child, in_heading=heading_context)
                if part:
                    parts.append(part)
            return sep.join(parts)

        if name in ["script", "style"]:
            return ""

        if name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(name[1])
            content = children_md("", heading_context=True).strip()
            if not content:
                return ""
            return ("#" * level) + " " + content + "\n\n"

        if name == "p":
            content = children_md("", heading_context=False)
            return (content.strip() + "\n\n") if content.strip() else ""

        if name in ["strong", "b"]:
            inner = children_md("", heading_context=in_heading)
            return inner if in_heading else f"**{inner}**"
        if name in ["em", "i"]:
            inner = children_md("", heading_context=in_heading)
            return inner if in_heading else f"*{inner}*"

        if name == "br":
            return "\n"

        if name == "img":
            src = node.get("src", "")
            alt = node.get("alt", "")
            return f"![{alt}]({src})\n\n" if src else ""

        if name == "a":
            href = node.get("href", "")
            text = children_md("", heading_context=in_heading) or href
            return f"[{text}]({href})" if href else text

        if name in ["ul", "ol"]:
            items: list[str] = []
            for i, li in enumerate(node.find_all("li", recursive=False), 1):
                li_parts: list[str] = []
                for child in getattr(li, "children", []):
                    piece = node_to_md(child, in_heading=False)
                    if piece:
                        li_parts.append(piece)
                item_text = "".join(li_parts).strip()
                if not item_text:
                    continue
                items.append(f"- {item_text}" if name == "ul" else f"{i}. {item_text}")
            return ("\n".join(items) + "\n\n") if items else ""

        if name == "blockquote":
            content = children_md("", heading_context=False).strip()
            return ("> " + content.replace("\n", "\n> ") + "\n\n") if content else ""

        if name in ["code", "kbd", "samp"]:
            inner = children_md("", heading_context=False)
            return f"`{inner}`"
        if name == "pre":
            inner = children_md("", heading_context=False)
            return f"```\n{inner}\n```\n\n"

        if name in [
            "div",
            "section",
            "article",
            "header",
            "footer",
            "main",
            "aside",
            "figure",
            "figcaption",
        ]:
            content = children_md("", heading_context=in_heading)
            if not content.strip():
                return ""
            return content if content.endswith("\n\n") else (content.rstrip() + "\n\n")
        return children_md("", heading_context=in_heading)

    md = node_to_md(root)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md
