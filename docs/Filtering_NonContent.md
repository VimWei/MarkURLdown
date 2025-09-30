# 过滤非正文指南（Generic 过滤与站点定制）

本指南描述在不开发专用处理器的前提下，通过“去壳”方式获得更干净 Markdown 的方法与顺序；也给出何时应升级为专用 handler 的明确标准。

## 总览：三种手段（由易到难）

- 方法1（首选）：启用 GUI 开关 → COMMON_FILTERS（零配置、保守去壳）
- 方法2：按域名的 DOMAIN_FILTERS（小改动，针对站点补强）
- 方法3（最后）：专用 handler（结构化提取/动态渲染/站点特性）

合并与优先级（仅在 filter_site_chrome=True 时生效）：

```
DOMAIN_FILTERS[域名]  >  COMMON_FILTERS
```

## 快速决策（60 秒）

1) 先勾选“过滤非正文”（GUI）并重试；观察日志“DOM过滤：移除了 X 个元素”。
- 若输出干净：完成。
- 若仍有明显站点壳：进入 2)。

2) 在 `DOMAIN_FILTERS[域名]` 添加 3–5 条保守选择器（如 header、侧边推荐、悬浮条）。
- 若已解决：完成。
- 若仅这次任务需要多删些：进入 3)。

3) 升级为专用 handler（需要正文容器提取、懒加载修复、外链清洗、作者/时间结构化，或必须 Playwright 渲染）。

## 方法1：GUI 开关 + COMMON_FILTERS（保守、零配置）

- 入口：在 GUI 勾选“过滤非正文”。
- 生效范围：仅 generic 处理器。
- 适用：通用去除 header/nav/footer/侧栏/评论/分享/广告/面包屑等。
- 日志观测：控制台将打印“DOM过滤：移除了 X 个元素”。
- 经验阈值：X 通常在 5–50 之间较合理；若 0，可能选择器未命中或页面为极简布局。
- 误删排查：切换开关做 A/B 比对，关注正文段落、图片是否显著减少。

位置：`markitdown_app/core/common_utils.py` 中的 `COMMON_FILTERS`。

## 方法2：按域名的 DOMAIN_FILTERS（定制补强）

- 位置：`markitdown_app/core/common_utils.py` 的 `DOMAIN_FILTERS`。
- 建议策略：
  - 宽进严控：先用宽松选择器（`.article-suspended-panel`），观察一段时间再细化；避免过度限定（如复合 class）。
  - 控制规模：每个域名 3–5 条“核心选择器”，避免膨胀。
  - 维护节拍：半年回顾一次，或由失败率/反馈触发修正。

示例（掘金 juejin.cn）：
```
"juejin.cn": [
  ".main-header", ".article-suspended-panel", ".article-suspended-sidebar",
  ".recommend-box", ".recommended-area", ".recommended-list", ".related-list",
  ".open-in-app", ".download-app", ".app-promo"
]
```

## 方法3：专用 handler（结构化/动态/站点特性）

升级触发条件：
- 需要正文容器精准提取（只保留 `.entry-content` 等）。
- 需要图片懒加载修复（`data-src` → `src`）、外链/重定向清洗。
- 需要标题/作者/时间等头部结构化输出。
- 必须使用 Playwright 进行动态渲染或反检测。

参照：`zhihu_handler.py`、`wordpress_handler.py`（保持完整 HTML，仅删除噪音 → 交给 MarkItDown）。

## 标题提取策略（过滤开启时）

- 优先：正文 H1（`h1.article-title`、`[itemprop=headline]`、`article h1`、`main h1`、`h1`）
- 其次：`<head><title>`
- 提示：在调整 `DOMAIN_FILTERS` 时谨慎避免删掉正文 H1。

## 调试与质量验收

- 日志关键词：
  - 启用过滤：看到“尝试通用过滤策略(HTML预过滤)…”
  - 命中过滤：看到“DOM过滤：移除了 X 个元素”
- A/B 比对：同一 URL 打开/关闭过滤，比较 Markdown 的噪音与正文差异。
- 简易质量门槛（建议人工参考）：正文行数、图片/链接数量、是否保留首个 H1。

## 常见问题（FAQ）

- Q：为什么明明启用过滤了，输出几乎没变化？
  - A：选择器未命中（站点结构变化/过度限定），先用更宽的选择器；或该站点本就无明显“壳”。

- Q：为什么过滤后标题变成了 URL ID？
  - A：正文 H1 可能被删掉或未找到；请检查 `DOMAIN_FILTERS` 是否误删标题节点。

- Q：能否“只保留正文容器、不要去壳”？
  - A：这是“白名单保留”策略，建议在专用 handler 实现（风险更高、跨站点不稳定）。

## 位置一览

- COMMON_FILTERS / DOMAIN_FILTERS：`markitdown_app/core/common_utils.py`
- GUI 开关（过滤非正文）：`markitdown_app/ui/pyside/gui.py`

## 示例站点：掘金（juejin.cn）

- 推荐先启用 COMMON_FILTERS；若仍有悬浮条/推荐区/APP 推广，再添加 `DOMAIN_FILTERS["juejin.cn"]` 中的核心选择器。
- 若一次性需要更“干净”的输出，在会话 JSON 填 `extra_exclude_selectors` 试用验证。

---

建议在 `reference/HANDLER_DEVELOPMENT_GUIDE.md` 的“内容过滤模式”小节中添加短链接指向本文档，以免处理器指南过长而分散注意力。

## 选择器写法速查（CSS Select for BeautifulSoup）

基本规则（传给 `soup.select(...)` 的 CSS 选择器）：

- 标签名：直接写标签名
  - 示例：`header`、`nav`、`footer`、`article`
- 类（class）：用点号前缀
  - 单一类：`.sidebar`、`.advertisement`
  - 多个类同时匹配（元素必须同时包含这些类）：`.article-viewer.markdown-body`
- ID：用井号前缀
  - 示例：`#header`、`#comments`
- 后代与子代
  - 后代（任意层级）：`header nav`、`.main .sidebar`
  - 直接子代（仅一层）：`article > h1`、`ul > li`
- 兄弟（同层）
  - 相邻兄弟：`h1 + p`
  - 通用兄弟：`h1 ~ p`
- 属性选择器
  - 精确匹配：`img[alt="logo"]`、`a[rel="nofollow"]`
  - 存在匹配：`img[loading]`（只要有该属性）
  - 前缀/后缀/包含：
    - 以前缀开头：`img[src^="https://"]`
    - 以后缀结尾：`img[src$=".gif"]`
    - 包含子串：`div[class*="suspend"]`
- 组合示例
  - 类和标签：`div.sidebar`（标签为 div 且带 sidebar 类）
  - 多条件：`div.sidebar .recommend-box a[href^="/"]`

进阶与注意事项：

- 多类名的匹配：`.a.b` 匹配同时包含 `a` 和 `b` 两个类的同一元素；不等同于 `.a .b`（后者是后代关系）。
- 转义与特殊字符：类名中若包含冒号、斜杠等特殊字符（来自框架生成），需加反斜杠转义，例如：`.hidden.text-sm.xl\:block`。
- 宽进严控：优先写“语义宽”的选择器（如 `.article-suspended-panel`），确认稳定后再细化；避免 `.a.b.c.d` 这类过度耦合导致 A/B 变体失效。
- 性能与稳定性：避免使用过深的层级链（如 `div > div > div > ...`），页面微调易失效；尽量依靠语义类名或稳定 ID。
- SoupSieve 支持：`bs4.select` 基于 SoupSieve，支持大多数 CSS4 选择器（含 `:not()`、属性操作符等）。如需复杂结构谓词（`:has()`），在低版本可能不可用，建议改用更稳妥的层级选择或先选后过滤。

验证方法：

- 浏览器 DevTools：在控制台中用 `document.querySelectorAll('选择器')` 验证命中数量；注意浏览器 DOM 与服务端渲染 HTML 可能不同（JS 动态渲染的节点在直连 HTML 中不存在）。
- 本地日志：运行后查看“DOM过滤：移除了 X 个元素”，若 X=0 基本可判定未命中。
- 渐进调试：先用宽选择器确保命中，再逐步收敛到更精准的类名/结构。

常用模式范例（可直接用于 `DOMAIN_FILTERS`）：

```
"example.com": [
  // 顶部与导航
  "header", ".header", "nav", ".nav",
  // 悬浮/侧边推荐
  ".suspension", ".article-suspended-panel", ".sidebar", ".recommended-area",
  // 分享与评论
  ".share", ".share-buttons", "#comments", ".comment-list",
  // 广告与面包屑
  ".ad", ".ad-banner", ".advertisement", ".breadcrumb", ".breadcrumbs",
]
```
