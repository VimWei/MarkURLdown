# Advanced Page 设计示例

## AdvancedPage 类设计

基于 MdxScraper 的 AdvancedPage，为 MarkdownAll 项目定制的高级选项页面。

### 功能特性

1. **用户数据目录管理**
   - 显示用户数据目录路径（只读）
   - 提供"打开"按钮直接访问数据目录

2. **配置管理**
   - 恢复默认配置功能
   - 配置重置和清理

3. **系统设置**
   - 日志级别设置
   - 调试模式开关
   - 语言选择下拉框
   - 缓存管理（可选扩展）

### 代码实现

```python
from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
)

from markdownall.models.config_models import AdvancedConfig


class AdvancedPage(QWidget):
    # Signals for communicating with MainWindow
    open_user_data_requested = Signal()
    restore_default_config_requested = Signal()
    log_level_changed = Signal(str)
    debug_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Label width for fields in this page
        _section_w = None

        # User data directory section
        data_section = QHBoxLayout()
        _lbl_data = QLabel("User Data Path:", self)
        _lbl_data.setProperty("class", "field-label")
        _lbl_data.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        data_section.addWidget(_lbl_data)
        data_section.addSpacing(8)

        self.edit_data_path = QLineEdit(self)
        self.edit_data_path.setReadOnly(True)
        # Always show as grey text to indicate non-editable
        self.edit_data_path.setProperty("class", "readonly-input")
        data_section.addWidget(self.edit_data_path, 1)

        self.btn_open_data = QPushButton("Open", self)
        self.btn_open_data.setFixedWidth(90)
        self.btn_open_data.setObjectName("open-data-button")
        data_section.addWidget(self.btn_open_data)

        layout.addLayout(data_section)

        # Configuration actions section
        config_section = QHBoxLayout()
        _lbl_config = QLabel("Config Actions:", self)
        _lbl_config.setProperty("class", "field-label")
        _lbl_config.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        config_section.addWidget(_lbl_config)
        config_section.addSpacing(8)

        self.btn_restore_default = QPushButton("Restore default config", self)
        self.btn_restore_default.setFixedWidth(150)
        self.btn_restore_default.setObjectName("restore-default-button")
        config_section.addWidget(self.btn_restore_default)

        # Add spacer to push button to the left
        config_section.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(config_section)

        # System settings section (optional)
        system_section = QHBoxLayout()
        _lbl_system = QLabel("System Settings:", self)
        _lbl_system.setProperty("class", "field-label")
        _lbl_system.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        system_section.addWidget(_lbl_system)
        system_section.addSpacing(8)

        # Log level selection
        log_level_frame = QHBoxLayout()
        log_level_label = QLabel("Log Level:", self)
        self.log_level_combo = QComboBox(self)
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.setFixedWidth(100)
        log_level_frame.addWidget(log_level_label)
        log_level_frame.addWidget(self.log_level_combo)

        # Debug mode checkbox
        self.debug_mode_cb = QCheckBox("Debug Mode", self)
        self.debug_mode_cb.setChecked(False)

        # Language selection
        language_frame = QHBoxLayout()
        language_label = QLabel("Language:", self)
        self.language_combo = QComboBox(self)
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("简体中文", "zh")
        self.language_combo.addItem("Auto", "auto")
        self.language_combo.setCurrentText("Auto")
        self.language_combo.setFixedWidth(100)
        language_frame.addWidget(language_label)
        language_frame.addWidget(self.language_combo)

        system_section.addLayout(log_level_frame)
        system_section.addSpacing(20)
        system_section.addWidget(self.debug_mode_cb)
        system_section.addSpacing(20)
        system_section.addLayout(language_frame)
        system_section.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(system_section)

        # Align section labels to the longest label width
        _section_w = max(
            _lbl_data.sizeHint().width(),
            _lbl_config.sizeHint().width(),
            _lbl_system.sizeHint().width(),
        )
        _lbl_data.setFixedWidth(_section_w)
        _lbl_config.setFixedWidth(_section_w)
        _lbl_system.setFixedWidth(_section_w)

        # Add some spacing at the bottom
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Connect signals
        self._connect_signals()

        # Initialize data path
        self._update_data_path()

    def _connect_signals(self):
        """Connect internal widget signals to page signals"""
        self.btn_open_data.clicked.connect(self.open_user_data_requested.emit)
        self.btn_restore_default.clicked.connect(self.restore_default_config_requested.emit)
        self.log_level_combo.currentTextChanged.connect(self.log_level_changed.emit)
        self.debug_mode_cb.stateChanged.connect(
            lambda checked: self.debug_mode_changed.emit(bool(checked))
        )
        self.language_combo.currentTextChanged.connect(
            lambda text: self.language_changed.emit(self.language_combo.currentData())
        )

    def _update_data_path(self):
        """Show user data directory path"""
        # Get the project root from parent
        project_root = self._get_project_root()
        if project_root:
            data_path = os.path.join(project_root, "data")
            self.edit_data_path.setText(data_path)
        else:
            self.edit_data_path.setText("data/ (relative to project root)")

    def _get_project_root(self) -> str | None:
        """Walk up the parent chain to find project root"""
        try:
            p = self.parent()
            for _ in range(6):
                if p is None:
                    break
                if hasattr(p, "root_dir"):
                    return getattr(p, "root_dir")
                if hasattr(p, "parent") and callable(p.parent):
                    p = p.parent()
                else:
                    break
        except Exception:
            return None
        return None

    def get_config(self) -> AdvancedConfig:
        """Get current page configuration as data class"""
        return AdvancedConfig(
            user_data_path=self.edit_data_path.text(),
            language=self.language_combo.currentData(),
            log_level=self.log_level_combo.currentText(),
            debug_mode=self.debug_mode_cb.isChecked(),
        )

    def set_config(self, config: AdvancedConfig) -> None:
        """Set page configuration from data class"""
        if config.user_data_path:
            self.edit_data_path.setText(config.user_data_path)
        if config.language:
            index = self.language_combo.findData(config.language)
            if index != -1:
                self.language_combo.setCurrentIndex(index)
        if config.log_level:
            self.log_level_combo.setCurrentText(config.log_level)
        self.debug_mode_cb.setChecked(config.debug_mode)
```

### 配置模型

```python
from dataclasses import dataclass

@dataclass
class AdvancedConfig:
    """Advanced configuration for MarkdownAll"""
    user_data_path: str = ""
    log_level: str = "INFO"
    debug_mode: bool = False
```

### 样式定义

```css
/* Advanced Page 样式 */
.field-label {
    font-weight: bold;
    color: #333;
}

.readonly-input {
    background-color: #f5f5f5;
    color: #666;
    border: 1px solid #ddd;
}

#open-data-button {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
}

#open-data-button:hover {
    background-color: #106ebe;
}

#restore-default-button {
    background-color: #d13438;
    color: white;
    border: none;
    border-radius: 4px;
}

#restore-default-button:hover {
    background-color: #b71c1c;
}
```

### 主窗口集成

```python
# 在 MainWindow 中添加 Advanced Page
self.tab_advanced = AdvancedPage(self)
self.tabs.addTab(self.tab_advanced, "Advanced")

# 连接信号
self.tab_advanced.open_user_data_requested.connect(
    lambda: self.filec.open_user_data_dir(self)
)
self.tab_advanced.restore_default_config_requested.connect(
    lambda: self.cfgc.restore_default_config(self)
)
self.tab_advanced.language_changed.connect(
    lambda lang: self.settings.set("advanced.language", lang)
)
self.tab_advanced.log_level_changed.connect(
    lambda level: self.settings.set("advanced.log_level", level)
)
self.tab_advanced.debug_mode_changed.connect(
    lambda debug: self.settings.set("advanced.debug_mode", debug)
)
```

### 功能说明

1. **用户数据目录**
   - 显示 `data/` 目录的完整路径
   - 提供"打开"按钮，直接打开文件管理器到该目录
   - 路径为只读显示，防止误操作

2. **配置操作**
   - "恢复默认配置"按钮，重置所有设置到默认值
   - 提供确认对话框防止误操作

3. **系统设置**
   - 日志级别选择：DEBUG、INFO、WARNING、ERROR
   - 调试模式开关：启用详细的调试信息输出

4. **扩展性**
   - 可以轻松添加更多高级选项
   - 支持缓存清理、性能设置等功能

### 与 MdxScraper 的区别

1. **移除 wkhtmltopdf 相关功能**：MarkdownAll 不需要 PDF 转换工具
2. **简化路径管理**：专注于用户数据目录管理
3. **添加日志管理**：适合 MarkdownAll 的调试需求
4. **保持核心功能**：用户数据访问和配置重置功能

这个设计既保持了 MdxScraper Advanced Page 的核心优势，又针对 MarkdownAll 的特点进行了优化。
