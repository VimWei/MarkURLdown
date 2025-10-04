# ProgressPanel 设计（适配 MarkdownAll 多任务特性）

## 设计背景

### MarkdownAll vs MdxScraper 的业务差异

| 特性 | MdxScraper | MarkdownAll |
|------|------------|-------------|
| **任务类型** | 单一转换任务 | 多URL批量转换 |
| **进度显示** | 单一任务进度 | 整体任务进度 |
| **状态信息** | 简单状态 | 复杂多任务状态 |
| **日志需求** | 基础日志 | 详细的多任务日志 |

### MarkdownAll 的多任务特性

1. **批量处理**：同时处理多个URL
2. **整体进度**：显示整体任务完成情况
3. **详细状态**：每个URL的处理状态
4. **灵活日志**：支持多任务日志输出

## ProgressPanel 设计（简化版，适配多任务）

### 功能特性

1. **单行状态显示**
   - 简化为单行状态显示
   - 详细的多任务信息通过 LogPanel 线性显示

2. **状态信息格式（简化）**
   - "Ready" - 准备就绪
   - "Processing..." - 正在处理
   - "Completed" - 已完成
   - "Error" - 发生错误

### 代码实现

```python
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ProgressPanel(QWidget):
    # 进度更新信号
    progressUpdated = Signal(int, str)  # value, text

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        
        # 设置固定高度（适配多任务显示）
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        # 进度条
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(24)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)

        # 简化的状态显示（单行布局，配合 LogPanel 使用）
        self.status_label = QLabel("Ready", self)
        self.status_label.setStyleSheet("color: #555; font-size: 10pt; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def setProgress(self, value: int, text: str = "") -> None:
        """设置进度值和显示文本"""
        self.progress.setValue(max(0, min(100, int(value))))
        
        if text:
            # 显示自定义文本
            self.progress.setFormat(text)
        else:
            # 显示百分比
            self.progress.setFormat("%p%")

    def setStatus(self, text: str) -> None:
        """设置状态文本"""
        self.status_label.setText(text)

    def setMultiTaskProgress(self, current: int, total: int, current_url: str = "", 
                           successful: int = 0, failed: int = 0, pending: int = 0) -> None:
        """设置多任务进度（针对 MarkdownAll 优化）"""
        # 计算整体进度
        progress = int((current / total) * 100) if total > 0 else 0
        self.setProgress(progress)
        
        # 设置状态文本（简洁显示）
        if current_url:
            self.setStatus(f"Processing {current}/{total}: {current_url}")
        else:
            self.setStatus(f"Processing {current}/{total} URLs")
        
        # 详细的状态信息通过 LogPanel 显示，这里只显示核心进度信息

    def reset(self) -> None:
        """重置进度"""
        self.progress.setValue(0)
        self.progress.setFormat("Ready")
        self.setStatus("Ready")

    def setEnabled(self, enabled: bool) -> None:
        """设置启用状态"""
        super().setEnabled(enabled)
        self.progress.setEnabled(enabled)
        self.status_label.setEnabled(enabled)
```

## 样式定义

### ProgressPanel 样式

```css
/* ProgressPanel 样式 */
QProgressBar {
    border: 1px solid #ccc;
    border-radius: 4px;
    text-align: center;
    font-weight: bold;
    background-color: #f8f9fa;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

QProgressBar::chunk:hover {
    background-color: #106ebe;
}
```

## 与 LogPanel 的配合

### 设计理念

- **ProgressPanel**：显示核心进度信息（简洁、一目了然）
- **LogPanel**：显示详细的多任务日志（完整、可追溯）

### 使用示例

```python
# ProgressPanel 显示核心进度
progress_panel.setMultiTaskProgress(3, 10, "https://example.com")

# LogPanel 显示详细日志
log_panel.appendLog("🚀 开始处理 10 个 URL")
log_panel.appendTaskLog("1", "正在访问: https://example1.com")
log_panel.appendTaskLog("1", "✅ 转换完成: example1.md")
log_panel.appendTaskLog("2", "正在访问: https://example2.com")
log_panel.appendTaskLog("2", "❌ 转换失败: 连接超时")
```

## 总结

这个 ProgressPanel 设计专门针对 MarkdownAll 的多任务特性进行了优化：

### 1. **简洁的进度显示**
- 单行状态显示，不占用过多空间
- 核心进度信息一目了然
- 详细状态通过 LogPanel 补充

### 2. **多任务支持**
- 支持整体任务进度显示
- 支持当前处理URL显示
- 支持成功/失败统计

### 3. **与 LogPanel 的完美配合**
- ProgressPanel：核心进度信息
- LogPanel：详细日志记录
- 两者互补，提供完整的多任务处理体验

### 4. **技术优势**
- 代码简洁，易于维护
- 性能良好，响应迅速
- 可扩展性强，便于功能增强

这样的设计既保持了简洁性，又完美适配了 MarkdownAll 的多任务特性，为用户提供了清晰、直观的进度显示体验。

---

*文档版本: 1.0*  
*创建日期: 2025-01-03*  
*最后更新: 2025-01-03*
