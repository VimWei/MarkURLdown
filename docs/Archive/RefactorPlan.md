# MarkURLdown 重构规划

本规划旨在在保持现有功能与体验不变的前提下，为未来扩展提供清晰、可演进的架构。

## 架构设计

### 目标分层（端口-适配器思想）

- **core/** (领域逻辑, 纯 Python、可测试、与 GUI 无关)
  - `handlers/` 站点/来源处理器（已实现统一架构）
    - `weixin_handler.py` 微信文章处理器（统一架构，支持为每个公众号配置内容过滤规则）
    - `zhihu_handler.py` 知乎文章处理器（统一架构，支持专栏和回答）
    - `wordpress_handler.py` WordPress文章处理器（统一架构，内容过滤）
    - `nextjs_handler.py` Next.js博客处理器（统一架构，静态博客支持）
    - `generic_handler.py` 通用处理器（统一架构，处理其他网站）
    - `others_handler.py` 未来可能的其他站点处理器
  - `crawlers/` 爬虫技术工具模块（可选，用于简单场景）
  - `converters/` 各输入类型的转换器（url/html/file: docx/pptx/pdf…）
  - `normalize.py`, `filename.py`, `images.py` 等纯函数
  - `registry.py` 处理器与转换器注册/选择
  - `types.py` 数据模型与协议（Protocol/Dataclass）
- **services/** (应用服务：批处理、线程、进度派发)
  - `convert_service.py` 负责批处理、停止标志、进度事件
- **ui/** (用户界面)
  - `tkinter/` (旧版 GUI)
  - `pyside/` (当前主 GUI)
  - `viewmodel.py`（UI 与服务层的桥：状态与命令）
  - `locales/` (多语言支持)
  - `assets/` (共用资源)
- **io/** (输入输出)
  - `config.py`（配置读写）
  - `writer.py`（保存 markdown、目录准备）
  - `session.py`（requests 会话构建）
- **启动入口** (应用启动)
  - `MarkURLdown.pyw` (主启动文件，包含splash screen和完整启动逻辑)

### 核心组件

- **启动入口**：`MarkURLdown.pyw` - 包含splash screen和完整启动逻辑
- **主GUI**：`markitdown_app/ui/pyside/gui.py` 中的 `PySideApp` 类
- **核心逻辑**：`markitdown_app/core/` - 处理器、转换器、工具函数
- **数据模型**：`markitdown_app/app_types.py` - 统一的数据结构
- **多语言支持**：`markitdown_app/ui/locales/` - 中英文语言包

### 目标结构

```
MarkItDown.vbs                  # VBScript启动器（可选）
MarkURLdown.pyw                 # 主启动文件（包含splash screen）
markitdown_app/
  core/
    handlers/                    # 站点处理器目录（已实现统一架构）
      __init__.py               # 统一导入接口
      weixin_handler.py         # 微信处理器（统一架构，支持为每个公众号配置内容过滤规则）
      zhihu_handler.py          # 知乎处理器（统一架构，支持专栏和回答）
      wordpress_handler.py      # WordPress处理器（统一架构，内容过滤）
      nextjs_handler.py         # Next.js博客处理器（统一架构，静态博客支持）
      generic_handler.py        # 通用处理器（统一架构，处理其他网站）
      others_handler.py         # 未来可能的其他站点处理器
    converters/                 # 输入类型转换器
      url_converter.py
      file_converter.py         # 未来文件转换器
    filename.py
    html_to_md.py
    images.py
    normalize.py
    registry.py                 # 注册系统
    types.py
  io/
    config.py
    logger.py
    session.py
    writer.py
  services/
    convert_service.py
    playwright_driver.py        # 统一的浏览器管理基础设施
  ui/
    viewmodel.py
    locales/                 # 多语言支持
      zh.json               # 中文语言包
      en.json               # 英文语言包
    assets/                 # 共用资源
      app_icon.ico          # 应用图标
      splash_*.png          # 启动画面图片
      screenshot_*.png      # 界面截图
    pyside/
      gui.py
  app_types.py                  # 数据模型与协议
```

### 数据模型

```python
@dataclass
class SourceRequest:
    kind: Literal["url","html","file"]
    value: str

@dataclass
class ConversionOptions:
    ignore_ssl: bool
    no_proxy: bool
    download_images: bool

@dataclass
class ConvertResult:
    title: str | None
    markdown: str
    suggested_filename: str

@dataclass
class ProgressEvent:
    kind: Literal["status","detail","progress_init","progress_step","progress_done","stopped","error"]
    # ... other fields
```

### 处理流程（可组合管线）

- **URL 场景:**
  1. `services.convert_service` 接收 `SourceRequest(kind="url")`
  2. `registry` 选择 `ContentSourceHandler` (e.g., WeixinHandler, ZhihuHandler)
  3. Handler 内部**内联实现**多种爬虫技术策略：
     - 优先使用轻量级策略（MarkItDown + httpx）
     - 失败时使用增强策略（Playwright + 反检测）
     - 再失败时使用备用策略（直接httpx）
     - 每个策略内部实现智能重试机制
  4. 转出 Markdown → normalize → 下载图片 → 生成文件名 → `io.writer` 保存
- **非 URL 场景 (html/docx/pdf):**
  - 直接由对应 Converter 处理，复用后续逻辑。

### 核心扩展点（接口/协议）

- **站点处理器 (Handlers):** 负责"来源特化"的抓取/清洗（如 Weixin、Zhihu）。
  - 选择依据：URL/host 或页面特征。
  - **内联实现多种爬虫技术**：每个处理器内部直接实现Playwright、httpx、Requests等策略。
  - 多策略尝试：优先使用最可靠的技术，失败时自动回退。
  - **完全定制化**：针对特定网站的反爬虫机制进行深度优化。
- **转换器 (Converters):** 负责"输入类型"的 Markdown 转换（url/html/file）。
  - 基于 MarkItDown，按负载类型调用不同路径。
- **注册表 (Registry):** 注册 handlers 与 converters，并按优先级挑选。

### 约定与策略补充

- **插件注册:** 初期使用静态列表注册，后期可切换为动态注册。
- **图片输出:** 默认 `output/img/`，文件名含时间戳与序号。
- **日志:** 核心与服务层使用 `logging`，GUI 监听进度事件做用户反馈。
- **文件命名:** 站点处理器遵循 `{site}_handler.py` 命名规则，技术实现作为内部细节。
- **目录结构:** 按功能职责组织，`handlers/` 按站点分类，`crawlers/` 作为可选工具模块。
- **实现策略:** 基于实际开发经验，复杂场景优先使用内联实现，通用类仅用于简单场景。
- **多语言支持:** 使用JSON格式语言包，支持中英文切换，语言包位于 `ui/locales/` 目录。
- **资源管理:** 共用资源（图标、启动画面等）统一放在 `ui/assets/` 目录，便于维护和更新。

## 架构演进

1. **启动方式演进**：
   - **原始设计**：`app/main_pyside.py` 和 `app/main_tk.py` 分别启动两套GUI
   - **实际实现**：`MarkURLdown.pyw` 作为唯一启动入口，包含splash screen和完整启动逻辑
   - **原因**：为了改进启动体验，避免"卡顿感"，提供即时反馈
   - **详细优化方案**：请参考 [启动速度优化方案](STARTUP_OPTIMIZATION.md)

2. **GUI策略调整**：
   - **原始设计**：同时支持PySide和Tkinter两套GUI，用户可选择
   - **实际实现**：主要使用PySide GUI，删除Tkinter GUI
   - **原因**：PySide功能更完整，维护成本更低，专注优化单一GUI体验

3. **目录结构简化**：
   - **原始设计**：`app/` 目录包含启动文件，`ui/tkinter/` 包含备用GUI
   - **实际实现**：删除 `app/` 和 `ui/tkinter/` 目录，启动逻辑移至根目录
   - **原因**：简化架构，减少不必要的抽象层和未使用的代码

4. **爬虫架构调整：**
    - **crawlers/ 目录定位调整**：从"核心爬虫技术模块"调整为"可选的爬虫技术工具模块"
    - **handlers/ 实现策略调整**：每个处理器内部直接实现多种爬虫策略，而非依赖通用类
    - **设计理念更新**：复杂场景优先使用内联实现，通用类仅用于简单场景和快速原型

5. **处理器架构统一（已完成）：**
    - **统一数据模型**：所有处理器使用相同的数据类（`CrawlerResult`、`FetchResult`）
    - **共享基础设施**：通过 `playwright_driver` 模块提供统一的浏览器管理
    - **一致的多策略实现**：MarkItDown、httpx、Playwright 等
    - **模块化设计**：清晰的职责分离，便于维护和扩展
    - **统一错误处理**：标准化的异常处理和重试机制

## 启动流程及优化

* 启动流程：

MarkURLdown.pyw (主启动文件)
├── 显示splash screen
├── 导入PySideApp类
├── 加载配置
├── 创建主窗口
└── 启动应用程序

* [启动速度优化方案](STARTUP_OPTIMIZATION.md)
    - VBS脚本优化和Python启动脚本优化
    - Splash screen实现和组件初始化策略
    - 启动流程对比和性能提升预期
    - 使用方法和进一步优化建议

## 爬虫框架设计指南

* [爬虫框架设计指南](CRAWLER_DESIGN_GUIDE.md)

- 爬虫框架的设计原则和实际开发经验
- **通用crawler类 vs 内联实现** 对比分析
- 技术选择策略和实现模式
- 未来扩展策略和最佳实践
- 完整的代码示例和开发建议

## 处理器开发指南

* [处理器开发指南](HANDLER_DEVELOPMENT_GUIDE.md)

- 四个核心处理器（WordPress、WeChat、Zhihu、NextJS）的完整案例分析
- 统一的处理器架构规范（目录结构、命名规范、注册方式、数据流）
- 五阶段处理流水线：抓取→解析→清理→转换→组装
- 多策略抓取机制（轻量→增强→备用）和共享浏览器管理
- 三种设计模式：反检测/行为模式、会话/规则驱动模式、简易站点处理框架
- 完整的开发模板和快速迁移指南（将简易站点框架应用到新站点）
- 性能优化建议、日志观测规范和测试策略
- 选择器域名覆盖机制和错误重试指导

## 测试策略

* [测试策略指南](TESTING_STRATEGY.md)

- **单元测试:** `core` 内的纯函数模块，使用Python内置的`unittest`框架。
- **集成测试:** 以本地样例与模拟会话验证端到端流程，测试处理器与转换器的协作。
- **环境测试:** 验证运行环境配置，确保所有依赖正确安装和网络连接正常。
- **调试工具:** 提供GUI和命令行调试工具，用于问题排查和性能分析。

## 后续实施步骤

随着核心架构重构和 PySide GUI 的初步实现，下一阶段的重点是优化用户体验和扩展核心功能。

1.  **✅ 优化启动体验：实现启动器与闪屏 (Launcher with Splash Screen) - 已完成**
    *   **目标:** 解决程序启动慢带来的"卡顿感"，提供即时反馈，提升专业性。
    *   **实施:** 已创建独立的启动入口 (`MarkURLdown.pyw`)，使用 `QSplashScreen` 在耗时任务（库导入、UI初始化）执行前显示启动画面。
    *   **结果:** 启动体验显著改善，用户立即看到反馈，避免了"卡顿感"。
    *   **详细方案:** 请参考 [启动速度优化方案](STARTUP_OPTIMIZATION.md)

2.  **✅ 实现爬虫框架：支持多种爬虫技术 (Crawler Framework) - 已完成**
    *   **目标:** 为复杂反爬虫场景提供可靠的爬虫解决方案，支持知乎等严格反爬虫网站。
    *   **实施:**
        - ✅ 实现了多策略爬虫技术（Playwright、httpx、MarkItDown）
        - ✅ 更新了微信、知乎、WordPress处理器，采用内联实现模式
        - ✅ 实现了多策略尝试和智能重试机制
        - ✅ 基于实际开发经验，采用内联实现而非通用crawler类
    *   **技术实现:**
        - **✅ 已完成**: 内联实现Playwright爬虫、httpx爬虫、MarkItDown集成
        - **✅ 已完成**: 多策略容错机制和智能重试
        - **🔄 未来扩展**: 代理池支持、缓存机制、性能监控
        - **设计理念**: 优先使用内联实现，通用类仅用于简单场景

3.  ✅ **扩展站点处理器 (Site-specific Handler Development) - 已完成**
    *   **目标:** 针对重点站点开发专门的处理器，实现爬虫策略选择、反检测机制、内容清洗、质量检测等完整功能，确保高质量的内容提取。
    *   **实施:** 已完成微信、知乎、WordPress、Next.js 四个核心处理器的结构统一和功能完善。每个处理器采用一致的结构模式：
        - **统一数据模型**: 所有处理器使用 `CrawlerResult` 和 `FetchResult` 数据类
        - **共享基础设施**: 统一使用 `playwright_driver` 模块提供浏览器生命周期管理
        - **多策略实现**: 每个处理器内部实现多种爬虫策略（MarkItDown、Playwright、httpx）
        - **一致错误处理**: 统一的异常处理和重试机制
        - **模块化设计**: 清晰的职责分离和可维护的代码结构
    *   **技术实现:**
        - ✅ **zhihu_handler.py**: 支持专栏文章和回答链接，集成反检测机制
        - ✅ **weixin_handler.py**: 处理微信公众号文章，支持poc_token验证，支持为每个公众号配置内容过滤规则
        - ✅ **wordpress_handler.py**: 专门处理WordPress站点，过滤非正文内容
        - ✅ **nextjs_handler.py**: 处理Next.js静态博客，保持完整HTML结构
        - ✅ **playwright_driver.py**: 提供统一的浏览器管理基础设施
    *   **架构优势:**
        - 代码复用性高，减少重复实现
        - 维护成本低，修改一处影响全局
        - 扩展性强，新处理器可快速基于现有模式开发
        - 测试友好，每个组件可独立测试
    *   **详情:** 请参考 [处理器开发指南](HANDLER_DEVELOPMENT_GUIDE.md)

4.  ✅ 加速模式（共享浏览器，按 URL 新建 Context）[默认开启，智能回退]
    *   **目标:** 在保证稳定性的前提下，处理多条 URL 时，减少每条 URL 的浏览器冷启动开销，提升批量处理速度。
    *   **设计:**
        - 浏览器 Browser 进程在"批处理任务"期间常驻；每个 URL 创建全新的 BrowserContext，保持上下文隔离与干净状态。
        - 首页引导（如站点首页建立会话）在该 URL 对应的 Context 内执行，随后新开 Page 访问目标文章。
        - 任务结束或空闲超时后关闭 Browser；异常时重启 Browser 并重试一次。
        - **智能回退机制**: 针对特定站点（如微信）的特殊需求，自动回退到独立浏览器模式。
    *   **配置项（默认开启）:**
        - `use_shared_browser`: bool（默认 true）。开启后启用"共享 Browser + 每 URL 新 Context"。
        - `idle_timeout_minutes`: int（建议 3–5）。空闲超时自动关闭 Browser（可选）。
        - `max_urls_per_browser`: int（建议 20–50）。超过阈值轮换重启 Browser（可选）。
        - `max_concurrent_contexts`: int（默认 5，当前串行场景无效；未来并发时作为限流参数）。
        - **处理器级配置**: 在 `registry.py` 中通过 `HandlerWrapper.prefers_shared_browser` 参数控制各处理器的浏览器模式偏好。
    *   **影响与取舍:**
        - 速度提升：减少反复启动 Browser 的开销，默认开启获得最佳性能。
        - 稳定性：Context 级隔离保留稳定性；仍需在异常时重启 Browser 保活。
        - 资源占用：Browser 常驻占用内存/句柄，可通过 idle timeout 与轮转策略控制。
        - 智能适配：根据站点特性自动选择最适合的浏览器模式。
    *   **实施路径（已完成）:**
        - 共享 Browser 生命周期绑定到批处理：`ConvertService` 批次开始创建、结束关闭。
        - **智能站点适配**：
          - 在 `registry.py` 中通过 `HandlerWrapper` 的 `prefers_shared_browser` 参数配置各处理器的浏览器偏好
          - `zhihu_handler.py`、`wordpress_handler.py`、`nextjs_handler.py`：`prefers_shared_browser=True`，使用共享 Browser
          - `weixin_handler.py`：`prefers_shared_browser=False`，强制使用独立浏览器模式（由于poc_token验证、反检测机制）
          - `generic_handler.py`：默认 `prefers_shared_browser=True`，支持共享浏览器
          - 通过 `should_use_shared_browser_for_url()` 函数根据URL自动选择浏览器模式
        - `ConversionOptions` 新增 `use_shared_browser`（默认 true）配置，`ConvertService` 根据处理器声明智能控制浏览器模式。

5.  **✅ 扩展知乎处理器：支持回答链接 (Zhihu Answer Support) - 已完成**
    *   **目标:** 扩展知乎处理器支持多种URL格式，特别是回答链接格式。
    *   **当前状况:** 仅支持专栏文章链接（`https://zhuanlan.zhihu.com/p/{文章ID}`）
    *   **目标格式:** 支持回答链接（`https://www.zhihu.com/question/{问题ID}/answer/{答案ID}`）
    *   **技术方案:** 扩展现有 `zhihu_handler` 的 `_process_zhihu_content` 函数
    *   **实施结果:**
        - ✅ 添加页面类型检测逻辑（专栏 vs 回答）
        - ✅ 为回答页面添加专门的内容选择器（`QuestionAnswer-content`）
        - ✅ 优化标题提取逻辑，支持回答页面结构（`QuestionHeader-title`）
        - ✅ 添加回答页面特有的内容清理逻辑
        - ✅ 测试验证，确保专栏文章功能完全不受影响
    *   **实际影响:** 显著提升知乎内容处理的覆盖范围，支持更多类型的知乎链接
    *   **测试结果:** 回答链接内容长度从115字符提升到6030字符，专栏文章功能保持正常

6.  ✅ **图片下载稳健性、格式识别与去重优化 (Robust Images + Magic Number + Dedup) - 已完成**
    *   **目标:** 解决图片下载失败映射错误、URL 扩展名与实际文件格式不一致，以及同一篇文章内重复图片的存储浪费，确保文件命名可追溯、处理可靠。
    *   **问题背景:**
        - 某些图片CDN（如知乎的 zhimg.com、微信的 qpic.cn）返回的图片URL扩展名可能与实际文件格式不符
        - 同一篇文章中可能存在重复的图片内容，导致不必要的存储空间浪费
        - 过去在个别情况下，下载失败的首图会被后续成功图片“占用”其预分配的文件名，造成引用错乱
        - Markdown 文件名与图片文件名的时间戳前缀可能不一致，影响通过文件名快速定位
    *   **技术实现:**
        - **失败下载的正确处理（关键修复）**:
          - 仅在图片实际下载成功后，才建立 `URL → 本地文件` 的映射
          - 下载失败的图片在 Markdown 中保留为原始链接，不再被其他成功图片占用其文件名
        - **可选的“事后紧凑重命名”开关（默认关闭）**:
          - 新增参数 `enable_compact_rename`（默认 False）。关闭后保留原始分配的序号，便于从断号看出失败下载或去重复用情况
          - 开启时才会按文章内出现顺序，为成功图片重新分配连续序号
        - **统一时间戳前缀**:
          - 在处理器中生成统一的时间戳 `conversion_timestamp`，同时传递给图片下载与 Markdown 文件名生成
          - 确保 Markdown 文件名与图片文件名共享同一时间戳前缀，便于定位与检索
        - **格式检测与修正**:
          - 针对特定CDN域名启用 Magic Number 校验：`zhimg.com`、`qpic.cn`、`mmbiz.qpic.cn` 等
          - 下载图片后读取文件头识别真实格式；当 URL 扩展名与真实格式不一致时，按真实格式原地重命名
          - 同步更新 Markdown 文件中的图片引用路径
        - **内容级智能去重**:
          - 基于 SHA-256 哈希进行内容级去重，确保相同内容的图片只存储一份
          - 流式计算哈希，边下载边计算，减少IO与内存开销
        - **并发与稳定性优化**:
          - 异步并发下载，限制全局与每主机的并发连接数
          - GitHub 旧式原图链接自动转换为 `raw.githubusercontent.com` 以避免重定向
    *   **实际效果:**
        - 修复“首图下载失败被后图占用”的引用错乱问题
        - 失败图片保持原始 URL，成功图片各自拥有独立且稳定的文件名
        - 通过文件名序号的“断号”即可洞察失败或去重复用情况
        - Markdown 与图片前缀一致，文件定位体验显著提升
        - 继续保证格式准确性与存储效率
    *   **性能优化:**
        - 仅对目标CDN域名启用格式检测，避免不必要的性能开销
        - 异步并发与流式哈希计算，提升处理速度并降低内存占用
    *   **相关文件:** `markitdown_app/core/images.py`, `markitdown_app/core/registry.py`, `markitdown_app/core/handlers/generic_handler.py`

7.  ✅ **Playwright 结构拆解与统一基础设施 (Playwright Refactoring & Unified Infrastructure) - 已完成**
    *   **目标:** 将各 handler 中的 Playwright 爬虫逻辑拆解为可复用、可测试的步骤式实现，建立统一的浏览器管理基础设施，支持共享浏览器和独立浏览器两种模式。
    *   **技术实现:**
        - **统一基础设施**: 创建 `playwright_driver.py` 模块，提供标准化的浏览器管理功能
        - **生命周期管理**: `new_context_and_page()` 和 `teardown_context_page()` 统一管理浏览器上下文
        - **反检测机制**: `apply_stealth_and_defaults()` 提供统一的反检测脚本注入
        - **页面操作助手**: 提供 `try_close_modal_with_selectors()` 等可复用函数
        - **内容获取**: `read_page_content_and_title()` 统一处理页面内容提取
        - **智能等待**: `wait_for_selector_stable()` 支持基于页面类型的智能等待策略
    *   **应用范围:**
        - ✅ **zhihu_handler.py**: 使用完整的 Playwright 基础设施，包括模态框处理和智能等待
        - ✅ **wordpress_handler.py**: 使用基础的生命周期管理和内容获取功能
        - ✅ **nextjs_handler.py**: 使用基础的生命周期管理和内容获取功能
        - ✅ **weixin_handler.py**: 保持独立浏览器模式，但可复用基础设施函数
    *   **架构优势:**
        - 代码复用性高，减少重复实现
        - 统一的错误处理和资源管理
        - 支持共享浏览器和独立浏览器两种模式
        - 便于测试和维护
        - 为未来新 handler 提供标准化模板
    *   **相关文件:** `markitdown_app/services/playwright_driver.py`

8.  **扩展输入源：支持文件类型转换 (File Converters)**
    *   **目标:** 扩展程序的核心能力，使其不再局限于 URL，可以处理本地文件。
    *   **实施:** 创建 `core/converters/file_converter.py`，集成 `python-docx`, `pdfminer.six` 等库，并在注册表中注册新的转换器。
