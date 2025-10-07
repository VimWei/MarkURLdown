# 处理器开发指南

本指南基于实际开发经验，总结了三个核心处理器（WordPress、WeChat、Zhihu）的设计理念和技术实现，为未来开发更多处理器提供参考和最佳实践。

## 处理器架构规范

### 目录结构

所有处理器必须放在 `src/markdownall/core/handlers/` 目录下：

```
src/markdownall/core/handlers/
├── __init__.py              # 统一导入接口
├── generic_handler.py       # 通用处理器
├── weixin_handler.py        # 微信处理器
├── zhihu_handler.py         # 知乎处理器
└── wordpress_handler.py     # WordPress处理器
```

### 命名规范

- **通用处理器**: `generic_handler.py` - 处理所有其他网站
- **特定站点处理器**: `{site}_handler.py` - 如 `weixin_handler.py`、`zhihu_handler.py`

### 导入方式

导入特定处理器
```python
from markdownall.core.handlers import fetch_weixin_article
from markdownall.core.handlers import fetch_zhihu_article
from markdownall.core.handlers import generic_convert_url
```

导入所有处理器
```python
from markdownall.core.handlers import *
```

查看处理器类型
```python
from markdownall.core.handlers import HANDLER_TYPES
print(HANDLER_TYPES)
```

### 注册新处理器

在 `src/markdownall/core/registry.py` 中：

1. 导入新处理器函数
2. 创建处理器函数（返回 `ConvertResult | None`）
3. 添加到 `HANDLERS` 列表

### 处理器在系统中的位置与数据流

- 上游（请求构建与调度）：
  - UI/服务层构建 `ConvertPayload` 与 `ConversionOptions`，并在 `payload.meta` 中传入 `logger`、`images_dir`、`shared_browser` 等上下文。
  - `registry.get_handler_for_url(url)` → 根据 URL 选择合适的 handler；`should_use_shared_browser_for_url(url)` 决定是否透传共享浏览器。
  - 调度入口：`registry.convert(payload, session, options)` 依次尝试 `HANDLERS` 列表中的处理器（命中即返回；否则回退到 Generic）。

- Handler 职责（站点内的获取与处理）：
  - 按“抓取→解析→清理→转换→组装”流水线处理，产出站点级 `FetchResult/markdown`。
  - 只关注站点特性与正文抽取，不负责全局图片下载、标题层级归一、文件命名等跨站点一致性工作。

- 下游（结果后处理与落盘）：
  - 在 `registry.convert()`（或服务层）执行统一的结果后处理：
    - 标题层级与文档规范化：`normalize_markdown_headings()`。
    - 图片下载与链接改写：`download_images_and_rewrite()`（按 `options.download_images` 与 `payload.meta.images_dir`）。
    - 文件名建议：`derive_md_filename()`。
  - 由 Writer/IO 层将 Markdown 与资源写入输出目录，并反馈到 UI。

- 回退与容错：
  - 特定站点 handler 返回 `None` 表示不适用或失败，调度层将尝试下一个 handler，最终回退到 `generic_handler.convert_url()`。

- 浏览器共享策略：
  - Handler 在 `registry.HANDLERS` 注册时通过 `prefers_shared_browser` 声明偏好；调度层据此动态开关共享浏览器并透传给 handler。

- 协作模式（统一约定）：
  - 返回契约：Handler 返回 `header_parts + 正文 Markdown`（`ConvertResult`）；不在 handler 内做图片下载/标题层级/文件命名。
  - 上层动作：集成层依据 `ConversionOptions` 与 `payload.meta` 执行 `download_images_and_rewrite()`、`normalize_markdown_headings()`、`derive_md_filename()` 等。
  - 行为解耦：是否使用共享/独立浏览器由调度层基于 `get_handler_for_url()` 与 `should_use_shared_browser_for_url()` 决策，handler 仅消费透传的 `shared_browser`。

- 数据契约（关键结构）：
  - `ConvertPayload`、`ConversionOptions`、`ConvertResult`（app_types）；站点内部常用 `CrawlerResult/FetchResult` 等中间结构以便解耦。

## 最佳实践

### 术语说明（统一定义）

- 多策略（multi-strategy）：针对同一 URL 依次尝试多种抓取方式（如轻量→增强→备用），在前者失败或内容无效时按序回退。
- 统一处理（unified processing）：所有爬取策略都返回原始 HTML，然后在站点内统一进行"解析→清理→转换→组装"的处理。
- 共享浏览器（shared browser）：同一 Browser 实例复用，不同 URL 各自新建 Context/Page；提高吞吐，但需按站点偏好选择。
- 独立浏览器（independent browser）：每个 URL 启动独立 Browser；稳定性更高，适合敏感/反爬严格站点。

### Handler 概述: 统一处理流水线

站点处理器遵循一致、模块化的流水线：分离「抓取 → 解析 → 清理 → 转换 → 组装」五阶段，并统一进出参，显著提升可读性与可维护性。

- 抓取 Fetch：基于多策略（httpx→Playwright）爬取完整HTML，尽量获取"全文"与完整上下文；支持共享浏览器透传。
- 解析 Parse：解析并分离 header_parts(标题、作者、时间等) 与正文内容 content_element，此时可依据站点特性选取相应的子集。
- 清理 Clean：对选定子集做必要的删除（广告等）与有界规范化（链接修复、懒加载归一、不可见字符清理、按站点定制规则等）。
- 转换 Convert：将清理后的正文HTML转 Markdown，保留结构语义。
- 组装 Assemble：将 header_parts 与正文 Markdown 按统一模板拼装，必要时下载图片并重写链接，产出一致格式的结果。

### 抓取 Fetch

- 多策略：优先httpx爬取（轻量快速），再Playwright爬取（完整稳定），失败时按序回退。
- 全量上下文：尽量抓取“全文”，为后续子集选择提供依据；共享浏览器可加速，敏感站点用独立浏览器。
- 重试与检测：策略内2次重试；抓取后进行长度/关键词/标题有效性检测。
- 常用实现切片：
  - `_try_httpx_crawler(session, url) -> FetchResult`
  - `_try_playwright_crawler(url, logger=None, shared_browser=None) -> FetchResult`
  - `_goto_target_and_prepare_content(page, url, logger=None) -> None`
  - Playwright driver：`new_context_and_page(...)`、`teardown_context_page(...)`、`read_page_content_and_title(page, logger=None)`
  - Generic 策略：`_try_lightweight_markitdown(url, session)`、`_try_enhanced_markitdown(url, session)`、`_try_direct_httpx(url, session)`、`_try_generic_with_filtering(url, session)`
- 参考：共享浏览器管理机制；Generic 的 `_try_*` 策略组合。

#### 共享浏览器管理机制

MarkdownAll 支持共享浏览器以加速多次抓取，但允许按站点声明偏好：需要更强隔离/反检测的站点使用独立浏览器，其余默认共享。

- 默认：共享浏览器开启时复用同一 Browser，每次 URL 新建 Context/Page。
- 站点偏好：在注册时声明 `prefers_shared_browser`；如声明为 False，调度层会在该 URL 前关闭共享并改用独立 Browser。
- 自动选择：通过 `get_handler_for_url(url)` 定位 handler → 读取 `prefers_shared_browser` → 决定实际模式。

* **如何声明/调整偏好**

- 在 `HANDLERS` 列表注册时：

```python
HandlerWrapper(_weixin_handler, "WeixinHandler", prefers_shared_browser=False)
HandlerWrapper(_zhihu_handler, "ZhihuHandler", prefers_shared_browser=True)
```

- 一旦修改偏好，无需改动调度层，`should_use_shared_browser_for_url(url)` 会自动生效。

提示：复杂反检测或强会话隔离站点优先用独立浏览器；其余站点用共享浏览器提升吞吐与速度。

#### 策略与重试

- 以「轻量→增强→备用」顺序尝试，单策略 2 次重试，策略间随机等待，降低被动防护风险。
- 每次获取后执行内容质量检测（长度、关键词、标题有效性），无效则重试或切换策略。
- 统一返回 `CrawlerResult/FetchResult/ConvertResult` 等既定数据结构。

#### 错误与重试指导（实践）

- 区分触发条件：
  - 网络/超时类：请求超时、连接错误 → 同策略立即重试（指数退避），最多 2 次。
  - 验证/反爬类：内容短且包含关键词（如 “验证/登录/访问被拒绝/环境异常/403/404”）→ 切换到下一策略（如从 httpx 切至 Playwright）。
  - 内容空/结构异常：正文容器未命中或 Markdown 过短 → 保持策略，调整等待/选择器或切下一策略。
- 关键词示例（可按站点扩展）：
  - 共性：验证/登录/访问被拒绝/403/404/环境异常
  - 微信：环境异常/需完成验证/去验证
  - 知乎：登录/验证/反爬/页面不存在
- 建议重试模板：
  - 每策略最多重试 2 次；策略间随机等待 1~4s；打印重试原因（网络/验证/内容短等）。
  - 成功判定优先长度阈值（如 > 1000 字符）与关键选择器命中，而非仅凭标题。
- 参考实现：`generic_handler.convert_url()` 的分策略重试；各 handler 的长度/关键词检测示例。

### 解析 Parse

- 头部信息：构建 `header_parts`（标题、来源URL、作者/时间等），保持简洁一至两行。
- 正文子集：按站点选择稳定容器（如 WordPress 的 `.entry-content`、知乎回答 `div.RichContent-inner`、微信 `div.rich_media_content`）。
- 页面类型：必要时先判别页面类型（如知乎回答/专栏），影响选择器与等待点。
- 常用实现切片：
  - 头部构建：`_build_{site}_header_parts(soup, url, title_hint=None) -> (title, header_parts | account_name, header_parts)`
  - 正文根元素：`_build_{site}_content_element(soup, page_type=None)`
  - 页面类型识别（按需）：`_detect_zhihu_page_type(url)` 等站点特定辅助。
  - 日志记录：通过 `logger` 参数记录关键步骤，如 `logger.parse_start()`、`logger.parse_title(title)`、`logger.parse_success(content_length)`。
- 参考：各站点 `_build_{site}_header_parts` 与 `_build_{site}_content_element`。

### 清理 Clean（删除-规范化）

- 删除（保守）：仅移除确定性非正文元素（广告、社交、导航、评论等），用明确选择器列表维护；微信可用账号规则提供器。
- 规范化（有界）：
  - 链接修复与反重定向（知乎的外链恢复、直答去壳、站内相对链接归一）。
  - 懒加载图片归一（`data-src`/`data-original` → `src`）。
  - 移除脚本/样式、零宽字符与异常空白。
- 各站点要点：
  - 知乎：恢复外链目标、移除“直答”跳转壳、标准化站内链接、清理零宽字符；删除量相对较小，侧重规范化与可读性。相关切片：`_clean_zhihu_external_links`、`_clean_zhihu_zhida_links`、`_normalize_zhihu_links`、`_strip_invisible_characters`、`_clean_and_normalize_zhihu_content`。
  - 微信：基于“账号规则提供器”按 styles/classes/ids 做保守删除，配合懒加载图片修复与脚本样式剔除；差异大、以规则集中维护为主。相关切片：`_get_account_specific_style_rules`、`_apply_removal_rules`、`_clean_and_normalize_weixin_content`。
  - WordPress：采用“减法策略”清单化删除（广告/社交/评论/推荐等），并做轻量规范化（懒加载归一、脚本样式移除）；不做结构搬移。相关切片：`unwanted_in_content`、`_clean_and_normalize_wordpress_content`。
  - NextJS：清理侧重懒加载图片归一、脚本样式移除，并清单化删除导航/目录/评论/页脚/社交/广告等非正文元素。相关切片：`_clean_and_normalize_nextjs_content`。

#### 选择器域名覆盖（Domain Override）

- 场景：同类站点整体规则通用，但个别域名存在额外广告块/导航方式，需追加或覆盖清理规则。
- 做法：
  - 在站点 handler 内维护 `domain -> selectors` 的映射；匹配到域名后将其合并到通用 `unwanted_selectors`/`unwanted_in_content`；
  - 推荐“增量+去重”的合并方式，避免影响其他域名；
- 示例（伪码）：

```python
  BASE_UNWANTED = [ '.ads', '.ad', '.social', '.comments', 'footer' ]
  DOMAIN_OVERRIDES = {
      'example.com': [ '.promo', '#sidebar-ads' ],
      'blog.example.cn': [ '.floating-share', '.subscribe-modal' ],
  }

  selectors = list(dict.fromkeys(BASE_UNWANTED + DOMAIN_OVERRIDES.get(hostname, [])))
  for sel in selectors:
      for el in content_elem.select(sel):
          el.decompose()
```

- 提示：覆盖仅作用于清理阶段；不要在覆盖中移动正文结构，保持“减法 + 规范化”的边界。

### 转换 Convert

- HTML→Markdown：优先 `html_fragment_to_markdown`；无法满足时再考虑最小必要的手动转换。
- 保持语义：保留标题、列表、表格、代码块等结构语义；避免在此阶段再做结构删改。
- 性能与稳定：仅对清理后的子集做转换，减少无关内容开销。
- 说明：`header_parts` 已经是 Markdown 片段，无需转换；转换仅针对正文 `content_element`。
- 常用实现切片：`html_fragment_to_markdown(content_elem)`；必要时使用站点内的最小手动转换函数。

### 组装 Assemble

- 头部 + 正文：用统一模板拼接 `header_parts` 与正文 Markdown，格式统一可读。
- 标题与层级：最终使用 `normalize_markdown_headings()` 确保唯一主标题。
- 图片与文件名：按需下载并重写图片链接；使用 `derive_md_filename()` 生成稳定文件名。
- 常用实现切片：
  - 一体化处理：`_process_{site}_content(html, title_hint=None, url=None) -> FetchResult`
  - 站点入口：`fetch_{site}_article(session, url, logger=None, shared_browser=None) -> FetchResult`
  - Registry 汇总：`convert(payload, session, options)` 与各 HandlerWrapper 声明。
  - 日志记录：通过 `logger` 参数记录处理进度，如 `logger.fetch_start("httpx")`、`logger.convert_success()`、`logger.url_success(title)`。
- 参考：各站点 `_process_{site}_content` 与 Registry 的最终整合流程。

### 性能建议（实践）

- 共享浏览器白名单：
  - 对稳定、无强验证的站点（如部分博客/NextJS/普通站点）可默认共享浏览器以提升吞吐；
  - 对敏感站点（微信/强反爬）保持独立浏览器，避免污染会话与提升稳定性；
  - 在 `registry` 侧基于域名/handler 偏好维护清单与决策，handler 无需关心。
- Playwright 等待策略：
  - 优先 `domcontentloaded` + 适度延时；在需要完整资源加载时再用 `networkidle`；
  - 对需交互的站点，使用“关键选择器稳定”策略（见 `wait_for_selector_stable` 思路）而非过长固定等待；
  - 减少不必要的滚动/截图等重操作，点击前尽量 `scroll_into_view_if_needed()` 并短暂等待。
- 轻量优先：
  - 能 httpx 就不使用 Playwright；能针对片段转换就不处理全文；
  - 清理阶段删除/规范化只针对正文容器，减少转换体量。

### 日志与观测建议（实践）

- **日志记录接口**：使用 `ConvertLogger` 接口进行结构化日志记录，直接显示在 `LogPanel` 中。优先使用细粒度日志方法提供更清晰的进度信息。
- **关键日志点**：
  - 策略尝试与结果：使用 `logger.fetch_start(strategy_name)`、`logger.fetch_failed(strategy_name, error)`、`logger.fetch_success(content_length)` 等细粒度方法。
  - 重要分支：使用 `logger.parse_start()`、`logger.parse_title(title)`、`logger.parse_success(content_length)` 记录解析阶段。
  - 内容质量：使用 `logger.parse_content_short(length, min_length)` 记录内容太短的情况。
  - 后处理摘要：使用 `logger.images_progress(total)`、`logger.images_done(total)`、`logger.url_success(title)` 等。
- **细粒度日志方法使用**：
  - `logger.fetch_start(strategy_name)` - 记录抓取开始
  - `logger.fetch_success(content_length)` - 记录抓取成功
  - `logger.fetch_failed(strategy_name, error)` - 记录抓取失败
  - `logger.fetch_retry(strategy_name, retry, max_retries)` - 记录重试
  - `logger.parse_start()` - 记录解析开始
  - `logger.parse_title(title)` - 记录解析到的标题
  - `logger.parse_content_short(length, min_length)` - 记录内容太短
  - `logger.parse_success(content_length)` - 记录解析成功
  - `logger.clean_start()` - 记录清理开始
  - `logger.clean_success()` - 记录清理完成
  - `logger.convert_start()` - 记录转换开始
  - `logger.convert_success()` - 记录转换完成
  - `logger.url_success(title)` - 记录URL处理成功
  - `logger.url_failed(url, error)` - 记录URL处理失败
  - `logger.task_status(idx, total, url)` - 多任务状态
  - `logger.images_progress/images_done()` - 图片下载进度
- **故障定位**：
  - 抓取问题优先看网络/等待/选择器日志；验证问题看关键词与页面标题；结构问题看正文容器未命中与删除清单。
- **最佳实践**：避免在循环内记录大量 DOM 内容；必要时输出片段长度或选择器数量即可。

### 测试建议（快查）

- 离线快照：
  - 抓取一份页面 HTML 存本地，离线调用解析/清理/转换，便于复现与调整选择器；
  - 对比线上抓取与离线结果差异，定位等待/动态内容造成的差别。
- 选择器回归：
  - 收集 5~10 个不同结构的示例 URL，定期跑一次，检查标题/正文/代码块/图片是否正常；
  - 修改清理清单前后，对比正文长度与关键选择器命中数。
- 示例 URL 清单：
  - 为每个 handler 维护小型示例清单（README 附录或注释中），覆盖不同页面类型；
  - 新增域名覆盖规则时，增补对应示例到清单中。
- 失败分析：
  - 优先查看“错误与重试”“日志与观测”推荐的关键日志点；
  - 验证类失败先人工打开页面确认是否触发了验证/登录/反爬。

## 案例分析

### 1. Zhihu (知乎) Handler - 反检测与行为处理
**设计理念：共享/独立浏览器择优 + 反检测脚本 + 兼容多页面类型 + 行为操作**

- 核心挑战：严格反爬策略、多种页面类型（回答、专栏等），以及动态交互（登录弹窗、展开阅读全文等）。
- 策略实现：优先使用共享浏览器（可配置为独立）；注入反检测脚本，访问后按页面类型等待关键选择器；必要时点击“展开阅读全文”。未知类型时可回退到通用多策略。
- 关键处理：
  - 反检测与准备：`_apply_zhihu_stealth_and_defaults`、`_goto_target_and_prepare_content`（关闭登录弹窗、展开按钮、等待稳定选择器）。
  - 头部与正文：`_build_zhihu_header_parts`、`_build_zhihu_content_element`（按回答/专栏差异）。
  - 清理与规范化：`_clean_and_normalize_zhihu_content`（恢复外链目标、去"直答"跳转壳、标准化站内链接、零宽字符清理）。
  - 转换与组装：正文用 `html_fragment_to_markdown`，与 `header_parts` 拼接。
  - 日志记录：通过 `logger` 参数记录关键步骤，如 `logger.fetch_start("playwright")`、`logger.parse_start()`、`logger.parse_title(title)`、`logger.url_success(title)`。
- 设计要点：最小必要操作驱动页面达到可读状态，减少破坏性；对未知/异常页面保留回退路径。
- 相关代码：`_try_playwright_crawler`、`_detect_zhihu_page_type`、`_try_click_expand_buttons`、`fetch_zhihu_article`

### 2. WeChat (微信) Handler - 反验证与账号规则清理
**设计理念：Playwright 独立浏览器 + 账号规则驱动清理**

- 核心挑战：poc_token 验证与复杂页面结构差异。
- 策略实现：仅使用 Playwright（强制独立浏览器），直达目标页并读取 HTML；随后在解析/清理阶段处理差异。
- 关键处理：
  - 头部与正文：`_build_weixin_header_parts`、`_build_weixin_content_element`。
  - 清理与规范化：`_get_account_specific_style_rules`（styles/classes/ids 规则提供器）+ `_apply_removal_rules` + `_clean_and_normalize_weixin_content`（懒加载归一、脚本样式剔除）。
  - 质量控制：长度/关键词检测与重试，避免环境异常/验证页面作为有效结果。
  - 日志记录：通过 `logger` 参数记录处理进度，如 `logger.fetch_start("playwright")`、`logger.fetch_failed("playwright", error)`、`logger.url_success(title)`。
- 设计要点：以“规则集中维护”应对不同公众号差异；抓取阶段尽量简化（可关闭图片/JS 以提高稳定性与速度）。
- 相关代码：`_try_playwright_crawler`、`_get_account_specific_style_rules`、`_apply_removal_rules`、`fetch_weixin_article`

### 3. WordPress Handler - 简易站点处理框架
**设计理念：多策略获取 + 模块化设计（可复用于多数简易站点）**

- 核心挑战：从多主题、多样式的 WordPress 页面中提取稳定正文
- 策略实现：优先 httpx 爬取原始 HTML → 统一进行内容处理；失败时使用 Playwright 爬取 HTML，再进入相同处理流程。
- 关键处理：
  - 头部信息与元数据：`_build_wordpress_header_parts`（调用 `_extract_wordpress_title` 与 `_extract_wordpress_metadata`）。
  - 正文定位：`_build_wordpress_content_element`（优先 `.entry-content` 及常见备选）。
  - 清理与规范化：`_clean_and_normalize_wordpress_content`（清单化删除广告/社交/评论/推荐等，懒加载归一/脚本样式移除）。
  - 转换：使用 `html_fragment_to_markdown` 将正文片段转为 Markdown，`header_parts` 直接拼接。
  - 日志记录：通过 `logger` 参数记录处理进度，如 `logger.fetch_start("httpx")`、`logger.parse_start()`、`logger.parse_success(content_length)`、`logger.url_success(title)`。
- 设计要点：结构具有灵活性，每个模块都方便个性化定制。
- 相关代码：`_try_httpx_crawler`、`_try_playwright_crawler`、`_process_wordpress_content`、`fetch_wordpress_article`

### 4. NextJS Handler - 现代博客多策略处理
**设计理念：多策略爬取（httpx/Playwright） + 统一内容处理 + 轻量规范化 + 清单化删除**

- 核心挑战：现代静态博客结构多样，但整体规范；需在正文容器未命中时对全文做安全清理。
- 策略实现：优先 httpx 爬取原始 HTML；必要时 Playwright 爬取 HTML。随后统一进行解析→正文定位（优先 `div.max-w-4xl.mx-auto.w-full.px-6`/`main`/`article`）→ 清理（懒加载归一、脚本样式移除、导航/目录/评论/社交/广告等删除）→ 转换。
- 关键处理：
  - 正文与清理：`_build_nextjs_content_element`、`_clean_and_normalize_nextjs_content`。
  - 转换与组装：`_process_nextjs_content` 调用 `html_fragment_to_markdown`；未定位到正文容器时对全文清理后再转换。
  - 日志记录：通过 `logger` 参数记录处理进度，如 `logger.fetch_start("httpx")`、`logger.clean_start()`、`logger.clean_success()`、`logger.url_success(title)`。
- 设计要点：偏向轻量规范化，删除清单明确；必要时对全文兜底处理，提升成功率。
- 相关代码：`_try_httpx_crawler`、`_try_playwright_crawler`、`_process_nextjs_content`、`fetch_nextjs_article`

### 技术架构对比

| 特性     | Zhihu                   | WeChat                        | WordPress                          | NextJS                         |
| ------   | ----------------------- | ----------------------------- | ---------------------------------- | ------------------------------ |
| 主要挑战 | 反爬虫与动态交互        | 验证与差异化页面              | 模块化设计的可定制性               | 结构多样下的稳健正文定位       |
| 技术重点 | 反检测脚本 + 行为模拟   | Playwright 独立 + 规则清理    | 多策略爬取 + 统一处理              | 多策略爬取 + 轻量清理           |
| 复杂度   | 最高                    | 中等                          | 中等                               | 中等                           |
| 成功率   | 受限（视策略与环境）    | 中等                          | 高                                 | 高（结构规范且兜底清理）       |
| 处理速度 | 慢                      | 中                            | 快（httpx）/中（Playwright）       | 快（httpx）/中（Playwright）   |
| 维护成本 | 高（策略与行为维护）    | 中（账号规则维护）            | 中（选择器与清单维护）             | 中（容器定位与清单维护）       |

### 设计模式总结

1. 反检测/行为模式（Zhihu）
- 适用场景：反爬严格且需交互的网站（多页面类型：回答/专栏等）
- 核心思路：共享/独立浏览器择优 + 反检测脚本 + 必要行为（关闭弹窗/展开）+ 类型化处理
- 技术栈：Playwright + 反检测脚本 + 行为模拟
- 优势：能在高压策略下获取内容
- 劣势：实现复杂、维护成本高

2. 会话/规则驱动模式（WeChat）
- 适用场景：需要处理验证与差异化页面
- 核心思路：Playwright 独立浏览器获取 + 账号规则提供器驱动的保守删除与规范化
- 技术栈：Playwright + 规则提供器 + 重试检测
- 优势：覆盖差异大的网站；清理策略可集中演进
- 劣势：成功率受站点策略影响

3. 简易站点处理框架（WordPress）
- 适用场景：多数非特定简易站点（博客/文章型页面）的通用处理
- 核心思路：多策略爬取（httpx→Playwright）+ 统一内容处理 + 渐进式"抓取→解析→清理→转换→组装"流水线
- 技术栈：BeautifulSoup + html_fragment_to_markdown（必要时手动转换）
- 优势：稳定、可维护；模块化强，易于个性化扩展与迁移到新站点
- 劣势：选择器与删除清单需要持续维护

## 模板及快速迁移指南

### 新 handler 开发模板

* 详见: [handler 模板](file:new_site_handler_template.py)

该模板包含：
- 多策略爬取实现（httpx/Playwright + 统一内容处理）
- 模块化流水线骨架（抓取→解析→清理→转换→组装）
- 完整的内容质量检查与重试机制
- 站点定制扩展点（选择器、规则、链接修复等）

### 快速迁移指南（将简易站点框架应用到新站点）

目标：在保持流水线一致性的前提下，最小代价适配一个新的文章型站点。

- 步骤 1：复制骨架
  - 参考 `reference/new_site_handler_template.py` 或 `wordpress_handler.py` 结构，新建 `{site}_handler.py`。
  - 保持函数切片：header 构建、正文定位、清理规范、一体化处理、抓取策略、主入口。

- 步骤 2：标题与元数据选择器
  - 在 `_extract_{site}_title` 与 `_extract_{site}_metadata` 中补充/调整选择器，确保标题、作者、时间能稳定命中。
  - 标题兜底：`<title>` 文本必要时去站点后缀（如 ` - SiteName`）。

- 步骤 3：正文容器候选
  - 在 `_build_{site}_content_element` 中配置稳定容器候选（如 `article/.entry-content/.post-content/main`）。
  - 若站点结构特殊，优先选择最内层语义容器作为片段根。

- 步骤 4：清理策略（减法 + 规范化）
  - 从 WordPress 的 `unwanted_in_content` 清单出发，删除广告/社交/评论/推荐等确定性非正文元素。
  - 统一规范化：懒加载图片归一、脚本/样式移除、（如需）链接归一与零宽字符清理。
  - 按域名扩展覆盖（domain override）：为特定站点追加/覆盖选择器条目，而不影响全局。

- 步骤 5：抓取与统一处理
  - 先试 httpx 爬取原始 HTML（更快、更稳），失败再用 Playwright；均返回原始 HTML 进入统一的内容处理流程。
  - 是否共享浏览器由 `registry` 按 handler 偏好自动决定，handler 内无需关心。
  - 通过 `logger` 参数记录关键步骤：使用细粒度日志方法如 `logger.fetch_start("httpx")`、`logger.fetch_success(content_length)`、`logger.fetch_failed("httpx", error)`、`logger.url_success(title)`。

- 步骤 5.1：细粒度日志方法使用指南
  - **抓取阶段**：使用 `logger.fetch_start(strategy_name)` 开始，`logger.fetch_success(content_length)` 成功，`logger.fetch_failed(strategy_name, error)` 失败，`logger.fetch_retry(strategy_name, retry, max_retries)` 重试。
  - **解析阶段**：使用 `logger.parse_start()` 开始，`logger.parse_title(title)` 记录标题，`logger.parse_content_short(length, min_length)` 内容太短，`logger.parse_success(content_length)` 成功。
  - **清理阶段**：使用 `logger.clean_start()` 开始，`logger.clean_success()` 完成。
  - **转换阶段**：使用 `logger.convert_start()` 开始，`logger.convert_success()` 完成。
  - **完成阶段**：使用 `logger.url_success(title)` 成功，`logger.url_failed(url, error)` 失败。

- 步骤 6：集成与注册
  - 在 `registry.py` 中新增 handler 包装并声明 `prefers_shared_browser`。
  - 返回 `ConvertResult` 前不做图片下载/标题层级/文件命名，交由上游统一处理（见“结果后处理（可选）”）。

- 验证建议
  - 用 3~5 个不同页面结构的示例 URL 验证：标题、正文、图片、代码块是否正常。
  - 遇到误删/漏删，优先调整选择器清单，而非重构 DOM 结构。
