# CommandPanel 设计（模仿 MdxScraper）

## 概述

直接模仿 MdxScraper 的 CommandPanel 设计，将会话管理、转换控制和进度显示整合在一个组件中。

## 功能特性

1. **会话管理按钮**：恢复、导入、导出配置
2. **转换控制按钮**：转换/停止操作
3. **进度条显示**：显示转换进度和状态信息
4. **固定高度**：120px，包含所有功能

## 代码实现

```python
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class CommandPanel(QWidget):
    # 会话管理信号
    restoreRequested = Signal()
    importRequested = Signal()
    exportRequested = Signal()
    # 转换控制信号
    convertRequested = Signal()
    stopRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Set fixed height for command panel (模仿 MdxScraper)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Row 1: restore/import/export (centered)
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 0, 0, 0)
        row_actions.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.btn_restore = QPushButton("Restore last config", self)
        self.btn_import = QPushButton("Import config", self)
        self.btn_export = QPushButton("Export config", self)
        for b in (self.btn_restore, self.btn_import, self.btn_export):
            b.setFixedWidth(150)
            b.setFixedHeight(32)
        self.btn_restore.clicked.connect(self.restoreRequested.emit)
        self.btn_import.clicked.connect(self.importRequested.emit)
        self.btn_export.clicked.connect(self.exportRequested.emit)

        row_actions.addWidget(self.btn_restore)
        row_actions.addSpacing(12)
        row_actions.addWidget(self.btn_import)
        row_actions.addSpacing(12)
        row_actions.addWidget(self.btn_export)
        row_actions.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(row_actions)

        # Row 2: convert (centered alone)
        row_convert = QHBoxLayout()
        row_convert.setContentsMargins(0, 0, 0, 0)
        row_convert.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.btn_convert = QPushButton("Convert to Markdown", self)
        self.btn_convert.setFixedWidth(220)
        self.btn_convert.setFixedHeight(45)
        self.btn_convert.setObjectName("convert-button")
        self.btn_convert.clicked.connect(self.convertRequested.emit)
        row_convert.addWidget(self.btn_convert)
        row_convert.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(row_convert)

        # Progress
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(20)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        root.addWidget(self.progress)

    # Public API (模仿 MdxScraper)
    def setProgress(self, value: int) -> None:
        """设置进度值"""
        self.progress.setValue(max(0, min(100, int(value))))
        # Only show percentage if no custom status text is set
        current_format = self.progress.format()
        if current_format == "Ready" or current_format == "%p%":
            self.progress.setFormat("%p%")

    def setProgressText(self, text: str) -> None:
        """设置进度条显示文本"""
        self.progress.setFormat(text)

    def setConvertButtonText(self, text: str) -> None:
        """设置转换按钮文本（用于转换/停止状态切换）"""
        self.btn_convert.setText(text)

    def setEnabled(self, enabled: bool) -> None:
        """设置启用状态"""
        super().setEnabled(enabled)
        # Keep buttons consistent when disabling panel
        for b in (self.btn_restore, self.btn_import, self.btn_export, self.btn_convert):
            b.setEnabled(enabled)
```

## 样式定义

```css
/* CommandPanel 样式 */
#convert-button {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11pt;
}

#convert-button:hover {
    background-color: #106ebe;
}

#convert-button:pressed {
    background-color: #005a9e;
}

QProgressBar {
    border: 1px solid #ccc;
    border-radius: 2px;
    text-align: center;
    background-color: #f8f9fa;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 1px;
}

QPushButton {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #5a6268;
}

QPushButton:pressed {
    background-color: #545b62;
}
```

## 主窗口集成

```python
# 在 MainWindow 中集成 CommandPanel
class MainWindow(QMainWindow):
    def __init__(self, project_root: Path):
        # ... 其他初始化代码 ...
        
        # 创建 CommandPanel
        self.command_panel = CommandPanel(self)
        
        # 连接信号
        self.command_panel.restoreRequested.connect(self._restore_last_config)
        self.command_panel.importRequested.connect(self._import_config)
        self.command_panel.exportRequested.connect(self._export_config)
        self.command_panel.convertRequested.connect(self._on_convert)
        self.command_panel.stopRequested.connect(self._on_stop)
        
        # 添加到 Splitter
        self.splitter.addWidget(self.command_panel)

    def _restore_last_config(self):
        """恢复最后配置"""
        # 实现配置恢复逻辑
        pass

    def _import_config(self):
        """导入配置"""
        # 实现配置导入逻辑
        pass

    def _export_config(self):
        """导出配置"""
        # 实现配置导出逻辑
        pass

    def _on_convert(self):
        """开始转换"""
        if self.is_running:
            self._on_stop()
            return
        
        self.is_running = True
        self.command_panel.setConvertButtonText("Stop")
        self.command_panel.setProgressText("Starting conversion...")
        
        # 开始转换逻辑
        self.start_conversion()

    def _on_stop(self):
        """停止转换"""
        self.is_running = False
        self.command_panel.setConvertButtonText("Convert to Markdown")
        self.command_panel.setProgressText("Stopped")
        
        # 停止转换逻辑
        self.stop_conversion()

    def updateProgress(self, value: int, text: str = ""):
        """更新进度（供外部调用）"""
        if text:
            self.command_panel.setProgressText(text)
        else:
            self.command_panel.setProgress(value)
```

## 使用示例

### 转换过程示例

```python
# 开始转换
main_window.command_panel.setConvertButtonText("Stop")
main_window.command_panel.setProgressText("Starting conversion...")

# 转换过程中
for i, url in enumerate(urls):
    progress = int((i / len(urls)) * 100)
    main_window.command_panel.setProgressText(f"Converting {i+1}/{len(urls)}: {url}")
    main_window.command_panel.setProgress(progress)
    
    # 模拟处理
    result = process_url(url)
    if result.success:
        main_window.log_panel.appendLog(f"✅ Success: {url}")
    else:
        main_window.log_panel.appendLog(f"❌ Failed: {url} - {result.error}")

# 完成
main_window.command_panel.setProgress(100)
main_window.command_panel.setProgressText("Conversion completed")
main_window.command_panel.setConvertButtonText("Convert to Markdown")
main_window.is_running = False
```

## 与 MdxScraper 的对比

| 功能 | MdxScraper | MarkdownAll |
|------|------------|-------------|
| 会话管理 | Restore/Import/Export config | Restore/Import/Export session |
| 转换按钮 | Scrape | Convert to Markdown |
| 进度显示 | 进度条 + 文本 | 进度条 + 文本 |
| 高度 | 120px | 120px |
| 布局 | 3行布局 | 3行布局 |

## 优势

1. **成熟稳定**：直接使用 MdxScraper 验证过的设计
2. **功能集中**：所有操作控制都在一个面板中
3. **用户熟悉**：与 MdxScraper 保持一致的用户体验
4. **开发简单**：减少组件数量，降低复杂度
5. **维护方便**：单一组件，易于维护和调试

## 总结

这个设计完全模仿了 MdxScraper 的成功模式，将会话管理、转换控制和进度显示整合在一个 CommandPanel 中。这样既保持了功能的完整性，又简化了架构设计，是一个务实且有效的方案。
