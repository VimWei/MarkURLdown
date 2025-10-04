# About Page 设计（参考 MdxScraper）

## 概述

基于 MdxScraper 的成功设计，为 MarkdownAll 项目定制关于页面，提供项目主页链接和版本检查功能。

## 功能特性

1. **项目主页链接**
   - 显示项目 GitHub 地址
   - 可点击链接，直接跳转到项目页面

2. **版本检查功能**
   - 显示当前版本信息
   - 提供版本更新检查按钮
   - 后台线程检查，不阻塞 UI
   - 实时显示检查状态和结果

## 代码实现

```python
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from markdownall.version import get_version_display


class VersionCheckThread(QThread):
    """Thread for checking version updates without blocking UI."""

    update_available = Signal(bool, str, str)  # is_latest, message, latest_version

    def __init__(self):
        super().__init__()
        # TODO: 实现版本检查服务
        # self.version_service = VersionCheckService()

    def run(self):
        """Run version check in background thread."""
        # TODO: 实现版本检查逻辑
        # is_latest, message, latest_version = self.version_service.check_for_updates()
        # self.update_available.emit(is_latest, message, latest_version or "")
        
        # 临时实现
        self.update_available.emit(True, "当前已是最新版本", "")


class AboutPage(QWidget):
    # Signals for communicating with MainWindow
    checkUpdatesRequested = Signal()
    openHomepageRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Row: Homepage (match Advanced page style)
        home_row = QHBoxLayout()
        _lbl_home = QLabel("Homepage:", self)
        _lbl_home.setProperty("class", "field-label")
        _lbl_home.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        _lbl_home.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        home_row.addWidget(_lbl_home)
        home_row.addSpacing(8)

        _val_home = QLabel(
            '<a href="https://github.com/VimWei/MarkdownAll">https://github.com/VimWei/MarkdownAll</a>',
            self,
        )
        _val_home.setOpenExternalLinks(True)
        _val_home.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        _val_home.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        home_row.addWidget(_val_home, 1)
        layout.addLayout(home_row)

        # Row: Update check
        update_row = QHBoxLayout()
        _lbl_update = QLabel("Updates:", self)
        _lbl_update.setProperty("class", "field-label")
        _lbl_update.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        _lbl_update.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        update_row.addWidget(_lbl_update)
        update_row.addSpacing(8)

        # Update status label
        self.update_status_label = QLabel("Click 'Check for Updates' to check", self)
        self.update_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.update_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        update_row.addWidget(self.update_status_label, 1)

        # Check for updates button
        self.check_updates_btn = QPushButton("Check for Updates", self)
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        self.check_updates_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        update_row.addWidget(self.check_updates_btn)

        layout.addLayout(update_row)

        # Make label columns share the same width
        max_label_w = max(_lbl_home.sizeHint().width(), _lbl_update.sizeHint().width())
        _lbl_home.setFixedWidth(max_label_w)
        _lbl_update.setFixedWidth(max_label_w)

        # Keep rows at the top; prevent vertical stretch of rows when resizing
        layout.addStretch(1)

        # Initialize version check thread
        self.version_thread = None

    def check_for_updates(self):
        """Start checking for updates in background thread."""
        if self.version_thread and self.version_thread.isRunning():
            return  # Already checking

        # Update UI to show checking status
        self.update_status_label.setText("Checking for updates...")
        self.check_updates_btn.setEnabled(False)
        self.check_updates_btn.setText("Checking...")

        # Create and start version check thread
        self.version_thread = VersionCheckThread()
        self.version_thread.update_available.connect(self.on_update_check_complete)
        self.version_thread.finished.connect(self.on_version_thread_finished)
        self.version_thread.start()

    def on_update_check_complete(self, is_latest: bool, message: str, latest_version: str):
        """Handle update check completion."""
        self.update_status_label.setText(message)

        # Update button text based on result
        if is_latest:
            self.check_updates_btn.setText("Check Again")
        else:
            self.check_updates_btn.setText("Check Again")

    def on_version_thread_finished(self):
        """Handle version check thread completion."""
        self.check_updates_btn.setEnabled(True)
        self.check_updates_btn.setText("Check Again")
        if self.version_thread:
            self.version_thread.deleteLater()
            self.version_thread = None

    def get_config(self) -> dict:
        """Get current configuration from the page."""
        return {
            "homepage_clicked": False,  # Track if homepage was accessed
            "last_update_check": None,  # Track last update check time
        }

    def set_config(self, config: dict) -> None:
        """Set configuration for the page."""
        # No specific configuration to set for About page
        pass
```

## 信号设计

### AboutPage 信号

```python
class AboutPage(QWidget):
    # 版本检查信号
    checkUpdatesRequested = Signal()
    # 主页访问信号
    openHomepageRequested = Signal()
```

### 主窗口信号连接

```python
# 在 MainWindow 中连接 About 页面信号
self.about_page.checkUpdatesRequested.connect(self.handle_check_updates)
self.about_page.openHomepageRequested.connect(self.handle_open_homepage)
```

## 样式设计

### 布局特点

1. **两行布局**：主页链接 + 版本检查
2. **标签对齐**：左侧标签右对齐，保持整齐
3. **按钮固定**：检查更新按钮固定宽度
4. **响应式**：标签列宽度自适应

### 样式类

```css
.field-label {
    font-weight: bold;
    color: #333;
    min-width: 80px;
}

QPushButton {
    min-width: 120px;
    padding: 4px 8px;
}

QLabel[href] {
    color: #0078d4;
    text-decoration: underline;
}
```

## 集成要点

### 1. 版本检查服务

需要实现版本检查服务，可以：
- 检查 GitHub Releases API
- 比较当前版本与最新版本
- 提供更新信息和建议

### 2. 国际化支持

```python
# 支持多语言
self.homepage_label.setText(self.translator.t("homepage_label"))
self.updates_label.setText(self.translator.t("updates_label"))
self.check_btn.setText(self.translator.t("check_updates_button"))
```

### 3. 配置持久化

```python
# 保存用户偏好
config = {
    "auto_check_updates": True,
    "last_check_time": "2025-01-03T10:00:00Z",
    "dismissed_version": "0.9.4"
}
```

## 测试要点

### 1. 功能测试

- [ ] 主页链接点击跳转
- [ ] 版本检查按钮响应
- [ ] 后台线程不阻塞 UI
- [ ] 检查结果正确显示

### 2. 界面测试

- [ ] 布局在不同窗口大小下正常
- [ ] 标签对齐整齐
- [ ] 按钮状态正确切换

### 3. 异常测试

- [ ] 网络断开时的处理
- [ ] 版本检查服务异常时的处理
- [ ] 线程安全测试

---

*文档版本: 1.0*  
*创建日期: 2025-01-03*  
*最后更新: 2025-01-03*
