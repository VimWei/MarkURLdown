# 转换为 Markdown 按钮调用流程分析

## 概述

本文档参考 `MdxScraper/docs/analysis/scrape_button_flow_analysis.md` 的结构，对 MarkdownAll 在按下“Convert to Markdown（转换为 Markdown）”按钮后的完整执行流程进行分层分析。重点拆解主要流程阶段（抓取 → 解析 → 清理 → 转换 → 组装 → 图片下载/链接改写 → 写入文件）以及进度与日志的细粒度上报路径，便于后续为 Progress 与 Log 提供更高粒度的进度信息。

- 架构特点：UI → ViewModel → Service（线程）→ Registry（调度/后处理）→ Handlers（站点实现）→ IO（写入）
- 进度与日志：通过 `ConvertLogger` 接口直接记录到 `LogPanel`，配合 `ProgressEvent` 进行进度条更新。

## 完整调用流程图

```
用户点击 Convert to Markdown 按钮
    ↓
CommandPanel.btn_convert.clicked → emit convertRequested
    ↓
MainWindow._on_convert()
    ↓
ViewModel.start() → ConvertService.run()
    ↓
ConvertService._worker()（后台线程）
    ↓
构建 ConvertPayload（携带 logger、should_stop、shared_browser 等）
    ↓
registry.convert(payload, session, options)
    ↓
按 URL 选择合适的 Handler（Weixin/Zhihu/WordPress/NextJS/Sspai/Appinn/Generic）
    ↓
Handler 执行：抓取 → 解析 → 清理 → 转换（HTML→Markdown 片段）→ 组装（header_parts + 正文）
    ↓
按需下载图片并重写链接（download_images_and_rewrite）
    ↓
结果后处理（标题层级归一、文件名建议）
    ↓
IO 写入 Markdown 文件（writer.write_markdown）
    ↓
Service 通过 logger 记录日志 + 发送进度事件 → MainWindow 更新进度条与 LogPanel
```

## 详细调用链分析

### 1. 按钮触发层（UI）

```821:853:c:\Apps\MarkdownAll\src\markdownall\ui\pyside\main_window.py
def _on_convert(self):
    if self.is_running:
        self._stop_conversion()
        return
    # 获取 URLs 与选项
    urls = self.basic_page.get_urls() or [...]
    out_dir = self.basic_page.get_output_dir().strip() or os.getcwd()
    options_dict = self.webpage_page.get_options()

    # UI 状态与初始日志
    self.is_running = True
    self.command_panel.setConvertingState(True)
    self.command_panel.set_progress(0, "Starting conversion...")
    self.log_info(f"Starting conversion of {len(urls)} URLs")

    # 构建请求与选项
    reqs = [SourceRequest(kind="url", value=u) for u in urls]
    options = ConversionOptions(**options_dict)

    # 启动（传入线程安全信号对象）
    self.vm.start(reqs, out_dir, options, self._on_event_thread_safe, self.signals)
```

- 角色：收集 UI 参数、切换按钮状态、初始化进度与日志，并通过 `ViewModel.start()` 发起转换。
- 进度入口：UI 在这里仅做"初始化显示"，真正的细粒度进度由 Service/Registry/Handlers 通过 `ConvertLogger` 直接记录到 `LogPanel`。

### 2. 视图模型层（ViewModel）

```25:34:c:\Apps\MarkdownAll\src\markdownall\ui\viewmodel.py
class ViewModel:
    def start(self, requests_list, out_dir, options, on_event, signals=None) -> None:
        self._service.run(requests_list, out_dir, options, on_event, signals)
    def stop(self, on_event) -> None:
        self._service.stop()
        on_event(ProgressEvent(kind="stopped", text="转换已请求停止"))
```

- 角色：极薄的一层，直接委托给 `ConvertService`，并转发停止事件。

### 3. 服务层（ConvertService，后台线程）

```21:52:c:\Apps\MarkdownAll\src\markdownall\services\convert_service.py
class ConvertService:
    def run(...):
        self._thread = threading.Thread(target=self._worker, args=(...), daemon=True)
        self._thread.start()
```

```74:139:c:\Apps\MarkdownAll\src\markdownall\services\convert_service.py
self._emit_event_safe(ProgressEvent(kind="progress_init", total=total, key="convert_init", data={"total": total}), on_event)
...
if getattr(options, "use_shared_browser", False):
    # 可选启动共享浏览器，并记录日志
    logger.info("启动共享浏览器...")
...
for idx, req in enumerate(requests_list, start=1):
    if self._should_stop:
        self._emit_event_safe(ProgressEvent(kind="stopped", key="convert_stopped"), on_event); return
    logger.task_status(idx, total, req.value)

    # 创建 LoggerAdapter 包装 MainWindow 的日志方法
    logger = LoggerAdapter(self._signals)

    # 基于 URL/Handler 偏好动态决定是否传入 shared_browser
    effective_shared_browser = ...

    payload = ConvertPayload(kind=req.kind, value=req.value, meta={
        "out_dir": out_dir,
        "logger": logger,
        "should_stop": lambda: self._should_stop,
        "shared_browser": effective_shared_browser,
    })

    result = registry_convert(payload, session, options)
    out_path = write_markdown(out_dir, result.suggested_filename, result.markdown)

    logger.success(f"转换完成: {out_path}")
    self._emit_event_safe(ProgressEvent(kind="progress_step", key="convert_progress_step", data={"completed": completed, "total": total}), on_event)
...
self._emit_event_safe(ProgressEvent(kind="progress_done", key="convert_progress_done", data={"completed": completed, "total": total}), on_event)
```

- 角色：
  - 启动后台线程，串行处理 URL 列表；可选开启/复用/关闭共享浏览器（提升吞吐）。
  - 为每个 URL 构建 `ConvertPayload`，注入 `logger`、`should_stop`、`shared_browser` 等上下文，调度至 Registry。
  - 通过 `LoggerAdapter` 将日志直接记录到 `LogPanel`，同时发送进度事件用于进度条更新。
  - 成功后写入 Markdown，并发出完成与进度步进事件。

- 日志与进度粒度：
  - **日志记录**：通过 `ConvertLogger` 接口直接记录到 `LogPanel`（`logger.info/success/warning/error/debug`）。
  - **进度事件**：`progress_init`（批处理开始）、`progress_step`（累计完成数）、`progress_done`（整体结束摘要）。
  - **任务状态**：`logger.task_status(idx, total, url)` 用于多任务分组显示。
  - **图片进度**：`logger.images_progress/images_done` 用于图片下载进度。

### 4. 调度与后处理层（Registry）

```470:477:c:\Apps\MarkdownAll\src\markdownall\core\registry.py
def convert(payload, session, options) -> ConvertResult:
    if payload.kind == "url":
        for h in HANDLERS:
            out = h(payload, session, options)
            if out is not None:
                return out
        return convert_url(payload, session, options)  # Generic 回退
    raise NotImplementedError
```

- 角色：
  - 根据 URL（由各 Handler 自身的匹配逻辑）依次尝试特定站点处理器，未命中则回退通用 `generic_handler.convert_url`。
  - 在各具体 `*_handler` 内部，完成“抓取 → 解析 → 清理 → 转换 → 组装”，再执行图片下载与链接改写和统一结果构造：

```62:116:c:\Apps\MarkdownAll\src\markdownall\core\registry.py
# 以 Weixin 为例（Zhihu/WordPress/NextJS/Sspai/Appinn 同理，细节因站点差异不同）
# 1) 抓取（可能 httpx/Playwright，多策略与共享浏览器透传）
#    - logger.info("开始抓取内容...")
# 2) 解析：标题/正文容器提取
#    - logger.info("解析页面结构...")
# 3) 清理：减法删除 + 规范化（懒加载/脚本样式/链接修复等，按站点实现）
#    - logger.info("清理页面内容...")
# 4) 转换：HTML 片段 → Markdown（正文），header_parts 与正文组装
#    - logger.info("转换为 Markdown...")
# 5) 结果后处理：标题层级归一（normalize_markdown_headings）
# 6) 图片下载与链接改写（download_images_and_rewrite），按 options.download_images
#    - logger.images_progress(total) / logger.images_done(total)
# 7) 生成建议文件名（derive_md_filename）
# 8) 返回 ConvertResult(title, markdown, suggested_filename)
```

- 共享浏览器策略：通过 `HandlerWrapper(..., prefers_shared_browser=...)` 声明偏好；`ConvertService` 在构建 payload 时据此传入/关闭共享浏览器。

### 5. IO 层（写入 Markdown）

```11:16:c:\Apps\MarkdownAll\src\markdownall\io\writer.py
def write_markdown(out_dir: str, filename: str, content: str) -> str:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path
```

- 角色：确保输出目录存在并写入文件，返回落盘路径供 Service 通过 `logger.success()` 记录到 `LogPanel`。

### 6. UI 进度与日志汇聚

```514:636:c:\Apps\MarkdownAll\src\markdownall\ui\pyside\main_window.py
def _on_event_thread_safe(self, ev: ProgressEvent):
    if ev.kind == "progress_init":
        self.command_panel.set_progress(0, "Starting conversion...")
        self.log_info(f"开始转换 {ev.data.get('total', 0)} 个URL")
    elif ev.kind == "progress_step":
        # 基于 completed/total 计算百分比，更新进度条与文本
        completed = ev.data.get("completed", 0)
        total = ev.data.get("total", 1)
        self.command_panel.set_progress(int(completed/total*100), f"已完成 {completed}/{total}")
    elif ev.kind == "progress_done":
        # 展示总体摘要（成功/失败/总数），结束状态复位
        completed = ev.data.get("completed", 0)
        total = ev.data.get("total", 0)
        self.log_success(f"转换完成: {completed}/{total} 个URL")
    elif ev.kind in ("stopped", "error"):
        # 结束并复位状态
        self.log_warning("转换已停止")
```

# 新的日志架构：ConvertLogger 接口
```python
class ConvertLogger(Protocol):
    def info(self, msg: str) -> None: ...
    def success(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def debug(self, msg: str) -> None: ...
    def task_status(self, idx: int, total: int, url: str) -> None: ...
    def images_progress(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None: ...
    def images_done(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None: ...
```

- 角色：通过 `LoggerAdapter` 将 `ConvertLogger` 接口适配到 `MainWindow` 的日志方法，负责：
  - **日志记录**：直接调用 `MainWindow` 的 `log_info/success/warning/error/debug` 方法记录到 `LogPanel`。
  - **进度更新**：通过 `ProgressEvent` 更新进度条数值与文本。
  - **多任务支持**：`task_status` 方法支持多任务分组显示。
  - **图片进度**：`images_progress/images_done` 方法支持图片下载进度显示。
  - **状态管理**：完成/停止/错误的 UI 状态复位。

## 主要流程阶段与可观测点

结合 `HANDLER_DEVELOPMENT_GUIDE.md` 的统一流水线约定，站点处理器内部遵循以下阶段。为实现更细粒度的进度展示，可在各阶段通过 `logger` 接口主动记录关键节点与摘要。

- **抓取 Fetch**（httpx/Playwright，多策略与重试）
  - 可观测点：`logger.info("开始抓取内容...")`、`logger.info("尝试策略 X...")`、`logger.warning("策略 X 失败，尝试下一种...")`、`logger.success("抓取成功")`。
- **解析 Parse**（标题与正文容器定位）
  - 可观测点：`logger.info("解析页面结构...")`、`logger.info("找到标题: ...")`、`logger.info("定位内容容器...")`。
- **清理 Clean**（删除 + 规范化）
  - 可观测点：`logger.info("清理页面内容...")`、`logger.info("移除广告和脚本...")`、`logger.info("规范化链接和图片...")`。
- **转换 Convert**（HTML 片段 → Markdown）
  - 可观测点：`logger.info("转换为 Markdown...")`、`logger.info("处理代码块和表格...")`。
- **组装 Assemble**（header_parts + 正文拼装）
  - 可观测点：`logger.info("组装最终文档...")`、`logger.success("文档组装完成")`。
- **图片下载与链接改写**（可选）
  - 可观测点：`logger.images_progress(total)`、`logger.images_done(total)`、`logger.info("图片下载完成")`。
- **写入文件**
  - 可观测点：`logger.success(f"文件已保存: {path}")`。

**日志记录建议**：
- 使用 `logger.info()` 记录一般进度信息。
- 使用 `logger.success()` 记录成功完成的操作。
- 使用 `logger.warning()` 记录警告信息（如策略失败、回退等）。
- 使用 `logger.error()` 记录错误信息。
- 使用 `logger.task_status()` 记录多任务状态。
- 使用 `logger.images_progress/images_done()` 记录图片下载进度。

## 扩展点与落地建议

- **共享浏览器偏好维护**：已在 `registry.HANDLERS` 声明；继续完善站点偏好将提升吞吐与稳定性。
- **细粒度日志记录**：在各 Handler 的关键阶段通过 `logger` 接口记录详细信息，直接显示在 `LogPanel` 中。
- **回退与容错**：维持"特定站点 → 通用"回退路径；将失败原因通过 `logger.error()` 记录，便于调试和统计。
- **多任务支持**：通过 `logger.task_status()` 和 `ProgressEvent` 的组合，支持多任务进度显示和日志分组。
- **图片下载进度**：通过 `logger.images_progress/images_done()` 提供细粒度的图片下载进度信息。

## 关键文件一览

| 层级 | 文件 | 职责 |
|------|------|------|
| UI | `ui/pyside/command_panel.py` | 按钮与进度条组件，发射 `convertRequested` |
| UI | `ui/pyside/main_window.py` | 连接信号、发起转换、汇聚进度与日志、控制 UI 状态 |
| ViewModel | `ui/viewmodel.py` | 转发 Start/Stop 到 Service |
| Service | `services/convert_service.py` | 后台线程、批处理、共享浏览器管理、事件上报、写文件 |
| 调度 | `core/registry.py` | Handler 调度、结果后处理（标题层级归一、图片下载与链接改写、文件名）|
| Handlers | `core/handlers/*.py` | 站点级实现：抓取→解析→清理→转换→组装 |
| IO | `io/writer.py` | 写入 Markdown 文件 |

以上分析为进度细化提供了清晰的日志记录位置：Service 层负责批处理与总控，通过 `LoggerAdapter` 将日志直接记录到 `LogPanel`；Handlers 内按阶段调用 `logger` 接口记录详细信息；UI 通过 `ProgressEvent` 更新进度条，通过 `ConvertLogger` 接口显示结构化日志信息。
