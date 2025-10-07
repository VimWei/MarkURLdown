# Logger 架构使用指南

## 概述

本文档详细介绍了 MarkdownAll 中新的日志记录架构，该架构基于 `ConvertLogger` 接口设计，旨在提供结构化、统一的日志记录体验，直接集成到 `LogPanel` 中显示。

本指南已更新以反映最近的稳定性修订：
- 通过 Qt 信号将后台线程日志安全地投递到主线程（“信号桥接”）。
- 图片下载在“专用线程 + 独立事件循环”中运行，避免与 GUI 事件循环互相干扰。
- `MainWindow` 的事件处理更健壮，避免 `None` 与 `int` 比较导致的异常。

## 架构设计理念

### 从 on_detail 到 logger 的演进

**旧架构问题**：
- `on_detail` 回调机制过于简单，只能传递字符串消息
- 缺乏结构化的日志级别和分类
- 难以在多任务场景下提供细粒度的进度信息
- 日志信息分散，难以统一管理和显示

**新架构优势**：
- 统一的 `ConvertLogger` 接口，支持多种日志级别
- 结构化日志记录，支持任务状态和进度信息
- 直接集成到 `LogPanel`，提供更好的用户体验
- 支持多任务场景下的日志分组和去重
- 线程安全：后台线程不直接触碰 UI，所有 UI 更新均由主线程执行

## 线程安全与信号桥接

### 为什么需要
Qt（PySide6）要求 UI 组件只能在主线程更新。直接从后台线程调用 UI 方法会随机崩溃或出现访问冲突。因此需要“信号桥接”：后台线程发出信号，主线程接收并更新 UI。

### 具体实现
- `ConvertService` 中持有 `signals`（主线程创建），后台工作线程只“发事件”：
  - `ProgressEvent(kind, key, text, data)` 通过 `signals.progress_event.emit(event)` 发送。
  - 无 `signals` 场景降级为直接回调或简单 `print`。
- `LoggerAdapter` 不再直接调用 UI；优先将日志包装为 `ProgressEvent` 发信号；若无信号，则仅在主线程直接调用 UI，后台线程降级 `print`。
- `MainWindow._on_event_thread_safe` 作为信号槽函数，在主线程内把事件映射为细颗粒度日志与进度。

### LoggerAdapter 行为摘要

`LoggerAdapter` 是线程安全的日志适配器，负责将服务层日志调用适配到 UI(LogPanel)：

- **线程安全机制**：优先通过 `signals.progress_event.emit(ProgressEvent(...))` 将日志事件发往主线程；若无信号，则在主线程直接调用 UI；在后台线程降级为 `print`。
- **事件映射**：
  - `info/success/warning/error` → 统一走 `_emit_progress()` 发 `ProgressEvent`（kind: status/detail/error）。
  - `task_status(idx, total, url)` → 发 `status` 事件，`data={idx,total,url}`。
  - `images_progress/images_done` → 发 `detail` 事件，`key` 分别为 `images_dl_progress/images_dl_done`，`data` 包含 `total/task_idx/task_total`。
- **细粒度日志**：所有细粒度阶段日志方法（如 `fetch_start`, `parse_start` 等）都通过 `_emit_progress()` 发送结构化事件。
- **降级策略**：当信号发送失败时，自动降级为直接 UI 调用（仅主线程）或 `print` 输出（后台线程）。

### MainWindow 事件处理规范

`MainWindow._on_event_thread_safe` 是线程安全的事件处理器，负责将 `ProgressEvent` 转换为直接的日志调用：

- **线程安全**：只在槽函数里更新 UI；不要在工作线程中直接访问 `LogPanel`。
- **健壮性处理**：对 `ev.data` 做健壮化：读取前判断是否为 `dict`；转换为 `int` 时注意 `None` 情况，避免 `None > 0` 一类比较。
- **事件映射**：
  - `progress_init/progress_step/progress_done` → 进度条与汇总；
  - `status/detail/error` → `log_info/log_success/log_warning/log_error`；
  - `images_dl_*` → 下载进度与完成提示（多任务合并/去重）；
  - `convert_detail_done` → 任务完成日志，支持多任务分组显示。
- **多任务支持**：通过 `appendTaskLog` 和 `appendMultiTaskSummary` 提供任务级别的日志分组。
- **去重机制**：图片下载日志使用 `_images_dl_logged_tasks` 集合避免重复记录。

## 图片下载与事件循环隔离

为避免与 Qt/其它协程循环发生冲突，图片下载的协程在“专用线程 + 新事件循环”中运行：
- 在新线程中 `asyncio.new_event_loop()` + `loop.run_until_complete()` 执行下载任务；
- 主线程仅接收下载进度事件与最终结果；
- 用户体验保持不变，但稳定性显著提升。

## ConvertLogger 接口定义

```python
from typing import Protocol

class ConvertLogger(Protocol):
    """用于在转换过程中输出日志到 UI(LogPanel) 的协议接口。"""
    
    # 基础日志方法
    def info(self, msg: str) -> None:
        """记录一般信息"""
        ...
    
    def success(self, msg: str) -> None:
        """记录成功信息"""
        ...
    
    def warning(self, msg: str) -> None:
        """记录警告信息"""
        ...
    
    def error(self, msg: str) -> None:
        """记录错误信息"""
        ...
    
    def debug(self, msg: str) -> None:
        """记录调试信息"""
        ...
    
    # 任务级别状态（可选）
    def task_status(self, idx: int, total: int, url: str) -> None:
        """记录多任务状态"""
        ...
    
    # 图片下载进度（可选）
    def images_progress(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None:
        """记录图片下载进度"""
        ...
    
    def images_done(self, total: int, task_idx: int | None = None, task_total: int | None = None) -> None:
        """记录图片下载完成"""
        ...
    
    # 细粒度阶段日志方法
    def fetch_start(self, strategy_name: str, retry: int = 0, max_retries: int = 0) -> None:
        """记录抓取开始"""
        ...
    
    def fetch_success(self, content_length: int = 0) -> None:
        """记录抓取成功"""
        ...
    
    def fetch_failed(self, strategy_name: str, error: str) -> None:
        """记录抓取失败"""
        ...
    
    def fetch_retry(self, strategy_name: str, retry: int, max_retries: int) -> None:
        """记录抓取重试"""
        ...
    
    def parse_start(self) -> None:
        """记录解析开始"""
        ...
    
    def parse_title(self, title: str) -> None:
        """记录解析到的标题"""
        ...
    
    def parse_content_short(self, length: int, min_length: int = 200) -> None:
        """记录内容太短的情况"""
        ...
    
    def parse_success(self, content_length: int) -> None:
        """记录解析成功"""
        ...
    
    def clean_start(self) -> None:
        """记录清理开始"""
        ...
    
    def clean_success(self) -> None:
        """记录清理完成"""
        ...
    
    def convert_start(self) -> None:
        """记录转换开始"""
        ...
    
    def convert_success(self) -> None:
        """记录转换完成"""
        ...
    
    def url_success(self, title: str) -> None:
        """记录URL处理成功"""
        ...
    
    def url_failed(self, url: str, error: str) -> None:
        """记录URL处理失败"""
        ...
    
    def batch_start(self, total: int) -> None:
        """记录批量处理开始"""
        ...
    
    def batch_summary(self, success: int, failed: int, total: int) -> None:
        """记录批量处理摘要"""
        ...
```

## 在 Handler 中使用 Logger

### 基本使用模式

```python
def fetch_example_article(
    session,
    url: str,
    logger: ConvertLogger | None = None,
    shared_browser: Any | None = None,
) -> FetchResult:
    """示例 Handler 函数 - 使用细粒度日志方法"""
    
    if logger:
        logger.fetch_start("httpx")
    
    try:
        # 执行抓取逻辑
        result = _try_httpx_crawler(session, url)
        
        if result.success:
            logger.fetch_success(len(result.html_markdown))
            return result
        else:
            logger.fetch_failed("httpx", result.error)
            return result
            
    except Exception as e:
        logger.fetch_failed("httpx", str(e))
        return FetchResult(title=None, html_markdown="", success=False, error=str(e))
```

### 多策略重试模式

```python
def fetch_with_retry(session, url: str, logger: ConvertLogger | None = None) -> FetchResult:
    """多策略重试示例 - 使用细粒度日志方法"""
    
    strategies = [
        ("httpx", lambda: _try_httpx_crawler(session, url)),
        ("playwright", lambda: _try_playwright_crawler(url, logger)),
    ]
    
    for i, (name, strategy) in enumerate(strategies, 1):
        if logger:
            logger.fetch_start(name)
        
        for retry in range(2):  # 每个策略最多重试2次
            try:
                result = strategy()
                
                if result.success:
                    if logger:
                        logger.fetch_success(len(result.html_markdown))
                    return result
                else:
                    if logger:
                        logger.fetch_failed(name, result.error)
                    
                    if retry < 1:  # 还有重试机会
                        if logger:
                            logger.fetch_retry(name, retry + 1, 2)
                        continue
                    else:
                        break
                        
            except Exception as e:
                if logger:
                    logger.fetch_failed(name, str(e))
                
                if retry < 1:
                    if logger:
                        logger.fetch_retry(name, retry + 1, 2)
                    continue
                else:
                    break
        
        # 策略间等待
        if i < len(strategies):
            time.sleep(1)
    
    if logger:
        logger.error("所有策略都失败")
    return FetchResult(title=None, html_markdown="", success=False, error="所有策略都失败")
```

### 图片下载进度记录

```python
def download_images_with_progress(content: str, logger: ConvertLogger | None = None) -> str:
    """图片下载进度记录示例 - 使用细粒度日志方法"""
    
    if not logger:
        return content
    
    # 统计图片数量
    img_count = len(re.findall(r'<img[^>]+src="([^"]+)"', content))
    
    if img_count == 0:
        logger.info("未发现图片，跳过下载")
        return content
    
    # 使用细粒度日志方法
    logger.images_progress(img_count)
    
    # 模拟下载过程
    downloaded = 0
    for i, img_url in enumerate(img_urls):
        try:
            # 下载图片逻辑
            download_image(img_url)
            downloaded += 1
            
            # 更新进度（LoggerAdapter会自动处理任务上下文）
            logger.images_progress(img_count, task_idx=i+1, task_total=len(img_urls))
            
        except Exception as e:
            logger.warning(f"图片下载失败: {img_url} - {e}")
    
    # 使用细粒度日志方法
    logger.images_done(downloaded)
    
    return content
```

### 完整处理流程示例

```python
def process_article_complete(
    session,
    url: str,
    logger: ConvertLogger | None = None,
    shared_browser: Any | None = None,
) -> FetchResult:
    """完整的文章处理流程示例 - 展示所有细粒度日志方法的使用"""
    
    if not logger:
        return FetchResult(title=None, html_markdown="", success=False, error="No logger")
    
    try:
        # 1. 抓取阶段
        logger.fetch_start("httpx")
        html_content = fetch_html(session, url)
        if not html_content:
            logger.fetch_failed("httpx", "Empty content")
            return FetchResult(title=None, html_markdown="", success=False, error="Empty content")
        
        logger.fetch_success(len(html_content))
        
        # 2. 解析阶段
        logger.parse_start()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取标题
        title = soup.find('title')
        if title:
            logger.parse_title(title.get_text().strip())
        
        # 提取正文
        content = extract_main_content(soup)
        if len(content) < 200:
            logger.parse_content_short(len(content))
            return FetchResult(title=None, html_markdown="", success=False, error="Content too short")
        
        logger.parse_success(len(content))
        
        # 3. 清理阶段
        logger.clean_start()
        cleaned_content = clean_html_content(content)
        logger.clean_success()
        
        # 4. 转换阶段
        logger.convert_start()
        markdown_content = html_to_markdown(cleaned_content)
        logger.convert_success()
        
        # 5. 图片处理
        img_count = count_images(markdown_content)
        if img_count > 0:
            logger.images_progress(img_count)
            markdown_content = download_images(markdown_content, logger)
            logger.images_done(img_count)
        
        # 6. 完成
        logger.url_success(title.get_text().strip() if title else "无标题")
        
        return FetchResult(
            title=title.get_text().strip() if title else "无标题",
            html_markdown=markdown_content,
            success=True
        )
        
    except Exception as e:
        logger.url_failed(url, str(e))
        return FetchResult(title=None, html_markdown="", success=False, error=str(e))
```

## 日志级别使用指南

### info() - 一般信息
用于记录正常的处理步骤和进度信息。

```python
logger.info("开始解析页面结构...")
logger.info("定位正文容器...")
logger.info("清理页面内容...")
logger.info("转换为 Markdown...")
```

### success() - 成功信息
用于记录成功完成的操作。

```python
logger.success("抓取成功")
logger.success("转换完成")
logger.success(f"文件已保存: {output_path}")
logger.success(f"策略 {name} 成功，内容长度: {len(content)} 字符")
```

### warning() - 警告信息
用于记录需要关注但不影响继续执行的情况。

```python
logger.warning("策略 X 失败，尝试下一种...")
logger.warning("内容太短，继续尝试下一个策略")
logger.warning("环境异常，尝试重试...")
logger.warning("图片下载失败: {url} - {error}")
```

### error() - 错误信息
用于记录严重的错误和异常情况。

```python
logger.error("抓取异常: {exception}")
logger.error("所有策略都失败")
logger.error("网络连接超时")
logger.error("页面解析失败")
```

### debug() - 调试信息
用于记录详细的调试信息，通常只在开发阶段使用。

```python
logger.debug(f"选择器命中: {selector}")
logger.debug(f"正文长度: {len(content)} 字符")
logger.debug(f"页面类型: {page_type}")
```

## 多任务场景下的日志记录

### task_status() - 任务状态
用于记录多任务处理的状态信息。

```python
# 在 ConvertService 中
for idx, req in enumerate(requests_list, start=1):
    logger.task_status(idx, total, req.value)
    # 处理单个任务...
```

### 图片下载进度
用于记录图片下载的进度信息。

```python
# 开始下载
logger.images_progress(total_images)

# 更新进度
logger.images_progress(total_images, task_idx=current, task_total=total_tasks)

# 下载完成
logger.images_done(downloaded_images)
```

## 最佳实践

### 1. 细粒度日志方法使用
- **优先使用细粒度方法**：使用 `fetch_start`, `parse_start`, `clean_start` 等细粒度方法替代通用的 `info()` 方法。
- **结构化信息**：细粒度方法自动提供结构化的日志信息，便于UI处理和用户理解。
- **阶段清晰**：每个处理阶段都有对应的开始和完成方法，让用户清楚了解处理进度。

```python
# 推荐：使用细粒度方法
logger.fetch_start("httpx")
logger.parse_start()
logger.clean_start()

# 避免：使用通用方法
logger.info("开始抓取...")
logger.info("开始解析...")
logger.info("开始清理...")
```

### 2. 错误处理与重试
- **策略失败记录**：使用 `fetch_failed` 记录具体策略的失败原因。
- **重试记录**：使用 `fetch_retry` 记录重试信息，包含重试次数和最大重试次数。
- **内容长度检查**：使用 `parse_content_short` 记录内容太短的情况。

```python
# 推荐：详细的错误和重试记录
logger.fetch_start("playwright")
try:
    result = playwright_strategy()
    if result.success:
        logger.fetch_success(len(result.content))
    else:
        logger.fetch_failed("playwright", result.error)
        if retry < max_retries:
            logger.fetch_retry("playwright", retry + 1, max_retries)
except Exception as e:
    logger.fetch_failed("playwright", str(e))
```

### 3. 图片下载进度
- **使用专用方法**：使用 `images_progress` 和 `images_done` 记录图片下载进度。
- **任务上下文**：LoggerAdapter 会自动注入任务上下文（task_idx, task_total），无需手动处理。
- **去重机制**：UI会自动处理多任务场景下的日志去重。

```python
# 推荐：使用专用图片进度方法
logger.images_progress(total_images)
# ... 下载过程 ...
logger.images_done(downloaded_images)

# LoggerAdapter 会自动处理任务上下文
# 在多任务场景下，UI会显示 "Task 1/3: Downloading images: 5 images"
```

### 4. 线程安全与信号桥接
- **不要直接调用UI**：在后台线程中不要直接调用 `LogPanel` 的方法。
- **依赖信号机制**：LoggerAdapter 会自动通过信号将日志事件发送到主线程。
- **降级处理**：当信号不可用时，LoggerAdapter 会自动降级为安全的处理方式。

```python
# 正确：LoggerAdapter 自动处理线程安全
logger.info("Processing...")  # 自动通过信号发送到主线程

# 错误：在后台线程直接调用UI
# self.log_panel.appendLog("Processing...")  # 会导致崩溃
```

### 5. 条件记录
- **始终检查logger**：在使用logger前检查是否为 `None`。
- **避免冗余日志**：细粒度方法已经提供了足够的上下文，避免重复记录相同信息。
- **静默处理**：某些方法（如 `convert_success`, `batch_summary`）被设计为静默，避免冗余日志。

```python
# 推荐：条件检查
if logger:
    logger.fetch_start("httpx")

# 推荐：利用静默设计
logger.convert_success()  # 静默，避免冗余
logger.batch_summary(success, failed, total)  # 静默，统计信息会合并显示
```

### 6. 多任务场景
- **任务状态记录**：使用 `task_status` 记录多任务状态。
- **批量处理**：使用 `batch_start` 记录批量处理开始。
- **任务分组**：UI会自动根据任务上下文进行日志分组显示。

```python
# 在 ConvertService 中
logger.batch_start(total_urls)
for idx, url in enumerate(urls, 1):
    logger.task_status(idx, total_urls, url)
    # 处理单个任务...
```

## 在现有代码中迁移

### 1. 函数签名更新
将 `on_detail` 参数替换为 `logger` 参数：

```python
# 旧版本
def fetch_article(session, url: str, on_detail=None, shared_browser=None):
    if on_detail:
        on_detail("开始抓取...")

# 新版本
def fetch_article(session, url: str, logger: ConvertLogger | None = None, shared_browser=None):
    if logger:
        logger.fetch_start("httpx")
```

### 2. 日志调用替换
将 `on_detail` 调用替换为相应的细粒度 `logger` 方法：

```python
# 旧版本
on_detail("抓取成功")
on_detail("策略失败")

# 新版本
logger.fetch_success(len(content))
logger.fetch_failed("httpx", error_message)
```

### 3. 参数传递
在调用链中正确传递 `logger` 参数：

```python
# 在 registry 中
def convert(payload, session, options):
    logger = payload.meta.get("logger")
    result = handler(payload, session, options)
    # 传递 logger 到子函数
    process_result(result, logger)

def process_result(result, logger):
    if logger:
        logger.parse_start()
        # 处理逻辑...
        logger.parse_success(len(result.content))
```

### 4. 细粒度方法迁移
将通用的日志调用迁移到细粒度方法：

```python
# 旧版本：通用日志
logger.info("开始抓取内容...")
logger.info("抓取成功")
logger.info("开始解析...")

# 新版本：细粒度日志
logger.fetch_start("httpx")
logger.fetch_success(len(content))
logger.parse_start()
```

## 调试和故障排除

### 1. 常见问题与解决方案

#### 线程安全问题
- **症状**：随机崩溃或访问冲突（Windows）
- **原因**：后台线程直接调用UI组件
- **解决**：确保使用LoggerAdapter，它会自动通过信号机制处理线程安全

#### 事件处理错误
- **症状**：大量 "Event handler error: '>' not supported between instances of 'NoneType' and 'int'"
- **原因**：`ev.data` 中的值可能为 `None`，直接比较导致异常
- **解决**：MainWindow的事件处理器已经包含健壮性检查，会自动处理 `None` 值

#### 图片下载日志重复
- **症状**：多任务场景下图片下载日志重复显示
- **原因**：没有使用去重机制
- **解决**：UI已经实现去重机制，使用 `_images_dl_logged_tasks` 集合避免重复

#### 复制日志失败
- **症状**：点击"Copy"后出现递归错误或剪贴板占用
- **原因**：通过信号链触发复制导致递归
- **解决**：MainWindow直接访问剪贴板，避免递归调用

### 2. 调试技巧

#### 启用调试模式
```python
# 在Advanced页面启用调试模式
# 这会显示更详细的调试信息
logger.debug("调试信息")
```

#### 检查信号连接
```python
# 确保信号正确连接
self.signals.progress_event.connect(self._on_event_thread_safe)
```

#### 验证LoggerAdapter状态
```python
# 检查LoggerAdapter是否正确初始化
if logger and hasattr(logger, '_signals'):
    print("LoggerAdapter has signals")
else:
    print("LoggerAdapter missing signals")
```

### 3. 性能考虑
- **避免频繁日志**：细粒度方法已经优化，避免过于频繁的日志记录
- **条件判断**：使用条件判断减少不必要的字符串格式化
- **静默设计**：某些方法被设计为静默，避免冗余日志输出

## 迁移清单（自检）

### 1. ConvertService ✅
- [x] `run(..., signals, ui_logger)`：保存 `signals`，后台线程创建 `LoggerAdapter(ui_logger, signals)`。
- [x] 通过 `_emit_event_safe()` 发关键阶段事件（共享浏览器启动/重启、进度、完成）。
- [x] 实现 `_TaskAwareLogger` 自动注入任务上下文。

### 2. LoggerAdapter ✅
- [x] 方法全部通过 `_emit_progress()` 发 `ProgressEvent`；无 `signals` 时降级策略明确。
- [x] 后台线程不直接触碰 UI。
- [x] 实现所有细粒度日志方法（fetch_start, parse_start, clean_start 等）。
- [x] 自动处理任务上下文注入。

### 3. MainWindow ✅
- [x] 连接 `signals.progress_event` → `_on_event_thread_safe`。
- [x] 事件处理对 `None` 和类型不匹配具备容错；进度条安全更新。
- [x] 复制日志使用剪贴板直接写入，避免递归/重入。
- [x] 实现多任务日志分组和去重机制。

### 4. 图片下载 ✅
- [x] 异步下载在专用线程 + 新事件循环中执行。
- [x] 提前初始化闭包使用到的映射（如 `url_to_local`）。
- [x] 通过LoggerAdapter发送进度事件，UI自动处理去重。

### 5. Handler实现 ✅
- [x] 函数签名更新为 `logger: ConvertLogger | None = None`。
- [x] 使用细粒度日志方法替代通用方法。
- [x] 正确处理错误和重试场景。

## 总结

新的 `ConvertLogger` 架构提供了：

1. **统一的接口**：所有组件使用相同的日志记录接口，支持细粒度日志方法
2. **结构化日志**：支持多种日志级别和特殊方法，自动提供上下文信息
3. **更好的用户体验**：直接集成到 `LogPanel` 中，支持多任务分组和去重
4. **多任务支持**：支持任务状态和进度记录，自动处理任务上下文
5. **线程安全**：通过信号桥接机制确保后台线程不直接操作UI
6. **易于维护**：清晰的接口设计，便于扩展和维护
7. **健壮性**：自动处理 `None` 值和类型不匹配，避免常见异常

通过遵循本指南的最佳实践，开发者可以创建出具有良好日志记录功能的 Handler，为用户提供清晰、有用的处理进度信息。细粒度日志方法的使用让用户能够清楚地了解每个处理阶段的进度，而线程安全机制确保了应用的稳定性。
