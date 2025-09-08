"""
公共工具函数 - 避免代码重复
"""

from bs4 import BeautifulSoup


# 保守的全局通用过滤选择器（尽量只移除站点外壳/噪音）
COMMON_FILTERS: list[str] = [
    # 文档头部（避免被当作正文）
    "head",

    # 导航/头部/页脚
    "nav", ".nav", "header", ".header", "#header", "footer", ".footer", ".site-footer",

    # 侧边栏/目录/浮动
    "aside", ".sidebar", ".toc", "#toc", ".table-of-contents", ".on-this-page", ".toc-container", ".toc-sidebar",
    ".floating", ".suspension", ".suspended", ".float",

    # 评论/分享/社交
    "#comment", "#comments", ".comments", ".comment-list", ".comment-form",
    ".share", ".share-buttons", ".social", ".social-links",

    # 广告/面包屑
    ".advertisement", ".ads", ".ad", ".ad-container", ".ad-banner",
    ".breadcrumb", ".breadcrumbs",
]


# 按域名的补充过滤（保守，可逐步维护）
DOMAIN_FILTERS: dict[str, list[str]] = {
    # 掘金 juejin.cn：去除顶部、悬浮操作区、侧边推荐、App推广等
    "juejin.cn": [
        "header",
        ".article-suspended-panel.dynamic-data-ready",
        "#sidebar-container", ".article-end",
        "#comment-box", 
        ".main-area.recommended-area.entry-list-container.shadow",
    ],
}


def apply_dom_filters(html: str, selectors: list[str]) -> tuple[str, int]:
    """根据 CSS 选择器移除元素，返回(过滤后HTML, 移除数量)。"""
    soup = BeautifulSoup(html, "lxml")
    removed = 0
    for selector in selectors:
        for elem in soup.select(selector):
            elem.decompose()
            removed += 1
    return str(soup), removed


def get_user_agents() -> list:
    """获取用户代理列表"""
    return [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]


def extract_title_from_html(html: str) -> str | None:
    """从HTML中提取标题"""
    try:
        soup = BeautifulSoup(html, 'lxml')
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else None
    except:
        return None


def extract_title_from_body(html: str) -> str | None:
    """从正文结构中提取更可靠的标题（优先 H1/语义headline）。"""
    try:
        soup = BeautifulSoup(html, 'lxml')
        # 常见正文标题选择器（按优先级）
        selectors = [
            'h1.article-title',
            '[itemprop=headline]',
            'article h1',
            'main h1',
            'h1',
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                text = node.get_text(strip=True)
                # 清理站点名后缀
                if ' - ' in text:
                    text = text.split(' - ')[0]
                return text
        return None
    except Exception:
        return None
