# 多任务日志分组功能设计

## 📋 **功能概述**

MarkdownAll支持批量URL转换，为了提供清晰的日志体验，实现了多任务日志分组功能。每个URL任务都有独立的日志标识，便于用户跟踪转换进度。

## 🎯 **设计目标**

1. **任务标识**: 每个URL任务都有清晰的标识（如 "Task 1/5"）
2. **分组显示**: 相关日志按任务分组显示
3. **进度跟踪**: 用户可以清楚看到每个任务的进度
4. **摘要统计**: 提供多任务完成的统计摘要

## 🏗️ **实现架构**

### 1. **LogPanel多任务支持**

```python
class LogPanel(QWidget):
    def appendTaskLog(self, task_id: str, message: str) -> None:
        """Append task-specific log (for multi-task operations)."""
        formatted_text = f"[{task_id}] {message}"
        self.appendLog(formatted_text)

    def appendMultiTaskSummary(self, successful: int, failed: int, total: int) -> None:
        """Append multi-task summary."""
        summary = f"Multi-task completed: {successful} successful, {failed} failed, {total} total"
        self.appendLog(summary)
```

### 2. **MainWindow事件处理**

```python
def _on_event_thread_safe(self, ev: ProgressEvent):
    """Enhanced event handler with multi-task logging support."""
    
    # Status events with task grouping
    if ev.kind == "status" and ev.data and "url" in ev.data:
        url = ev.data["url"]
        idx = ev.data.get("idx", 0)
        total = ev.data.get("total", 0)
        
        # Use task-specific logging for multi-task operations
        if total > 1:
            task_id = f"Task {idx}/{total}"
            self.log_panel.appendTaskLog(task_id, f"Processing: {url}")
        else:
            self.log_info(f"Processing URL: {url}")
    
    # Detail events with task grouping
    elif ev.kind == "detail" and ev.key == "convert_detail_done":
        path = ev.data.get("path", "")
        if ev.data.get("total", 1) > 1:
            idx = ev.data.get("idx", 0)
            total = ev.data.get("total", 0)
            task_id = f"Task {idx}/{total}"
            self.log_panel.appendTaskLog(task_id, f"Conversion completed: {path}")
        else:
            self.log_success(f"Conversion completed: {path}")
    
    # Progress completion with summary
    elif ev.kind == "progress_done":
        if ev.data and "completed" in ev.data and "total" in ev.data:
            completed = ev.data["completed"]
            total = ev.data["total"]
            if total > 1:
                successful = ev.data.get("successful", completed)
                failed = ev.data.get("failed", total - completed)
                self.log_panel.appendMultiTaskSummary(successful, failed, total)
            else:
                self.log_success("Conversion completed")
```

## 📊 **日志显示效果**

### 单任务转换
```
[14:30:15] ℹ️ Starting conversion of 1 URLs
[14:30:16] ℹ️ Processing URL: https://example.com
[14:30:18] ✅ Conversion completed: /output/example.md
[14:30:18] ✅ Conversion completed
```

### 多任务转换
```
[14:30:15] ℹ️ Starting conversion of 3 URLs
[Task 1/3] ℹ️ Processing: https://example1.com
[Task 1/3] ✅ Conversion completed: /output/example1.md
[Task 2/3] ℹ️ Processing: https://example2.com
[Task 2/3] ✅ Conversion completed: /output/example2.md
[Task 3/3] ℹ️ Processing: https://example3.com
[Task 3/3] ✅ Conversion completed: /output/example3.md
[14:30:25] Multi-task completed: 3 successful, 0 failed, 3 total
```

## 🔧 **技术实现细节**

### 1. **任务标识生成**
- 格式: `Task {current}/{total}`
- 示例: `Task 1/5`, `Task 2/5`, `Task 3/5`

### 2. **多任务检测**
- 通过 `ev.data.get("total", 1) > 1` 检测是否为多任务
- 单任务使用普通日志，多任务使用分组日志

### 3. **数据传递**
- `idx`: 当前任务索引（从1开始）
- `total`: 总任务数
- `url`: 当前处理的URL
- `path`: 转换完成的文件路径

### 4. **统计摘要**
- `successful`: 成功完成的任务数
- `failed`: 失败的任务数
- `total`: 总任务数

## 🎨 **用户体验**

### 优势
1. **清晰的任务跟踪**: 用户可以清楚看到每个任务的进度
2. **分组显示**: 相关日志按任务分组，避免混乱
3. **统计摘要**: 提供完整的转换统计信息
4. **向后兼容**: 单任务转换仍然使用简洁的日志格式

### 适用场景
- **批量转换**: 处理多个URL时提供清晰的任务跟踪
- **调试分析**: 便于定位特定任务的问题
- **进度监控**: 实时了解转换进度

## 📝 **使用示例**

### 业务层调用
```python
# 在convert_service.py中
def _emit_status_event(self, idx, total, url):
    """发送状态事件，支持多任务分组"""
    self._emit_event_safe(
        ProgressEvent(
            kind="status",
            data={"idx": idx, "total": total, "url": url}
        ),
        on_event
    )

def _emit_completion_event(self, idx, total, path):
    """发送完成事件，支持多任务分组"""
    self._emit_event_safe(
        ProgressEvent(
            kind="detail",
            key="convert_detail_done",
            data={"idx": idx, "total": total, "path": path}
        ),
        on_event
    )
```

### 日志输出
```
[14:30:15] ℹ️ Starting conversion of 5 URLs
[Task 1/5] ℹ️ Processing: https://site1.com
[Task 1/5] ℹ️ Downloading images: 25% (3 images)
[Task 1/5] ✅ Images downloaded: 12 images
[Task 1/5] ✅ Conversion completed: /output/site1.md
[Task 2/5] ℹ️ Processing: https://site2.com
[Task 2/5] ✅ Conversion completed: /output/site2.md
...
[14:30:45] Multi-task completed: 5 successful, 0 failed, 5 total
```

## 🔄 **向后兼容性**

- **单任务**: 继续使用简洁的日志格式
- **多任务**: 自动启用任务分组功能
- **现有代码**: 无需修改，自动适配

---
*文档版本: 1.0*  
*创建日期: 2025-01-05*  
*最后更新: 2025-01-05*
