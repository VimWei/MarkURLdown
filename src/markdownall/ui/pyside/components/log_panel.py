"""
Log Panel Component for MarkdownAll GUI.

This component handles detailed log information display and management.
Based on the Log_Integration_Analysis.md specification, adopting MdxScraper's简洁设计.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class LogPanel(QWidget):
    """
    Log panel component for detailed log information display.

    This component contains:
    - Scrollable log text area
    - Log operation buttons (clear, copy)
    - Adopts MdxScraper's simple design
    """

    # Log operation signals
    logCleared = Signal()
    logCopied = Signal()

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator

        # Setup UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the UI layout for log panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Log text area
        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        # Localized placeholder text
        if self.translator:
            self.log_text.setPlaceholderText(self.translator.t("log_placeholder"))
        else:
            self.log_text.setPlaceholderText("log message")
        # Style will be applied by theme
        layout.addWidget(self.log_text)

        # Log operation buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.setObjectName("log-clear-button")
        self.clear_btn.setFixedSize(70, 22)  # 更小的尺寸

        self.copy_btn = QPushButton("Copy", self)
        self.copy_btn.setObjectName("log-copy-button")
        self.copy_btn.setFixedSize(70, 22)  # 更小的尺寸

        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addStretch(1)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect internal signals."""
        self.clear_btn.clicked.connect(self._clear_log)
        self.copy_btn.clicked.connect(self._copy_log)

    def _clear_log(self):
        """Clear log content."""
        self.log_text.clear()

    def _copy_log(self):
        """Copy log content to clipboard."""
        try:
            from PySide6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            text = self.log_text.toPlainText()
            # 防止递归：只做一次设置，不触发任何自定义 copy 操作
            clipboard.setText(text)
            # 成功发信号（供 UI 上层提示），但不要在信号槽里再次调用 _copy_log
            self.logCopied.emit()
        except Exception as e:
            # 剪贴板占用等情况，优雅降级写入日志区域
            self.appendLog(f"Copy to clipboard failed: {e}")

    # Public API (adopting MdxScraper's simple design)
    def appendLog(self, text: str) -> None:
        """Append log text (main method for log output)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}"

        # Append to log text area
        self.log_text.append(formatted_text)

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def addLog(self, text: str, level: str = "INFO") -> None:
        """Add log text with level (for compatibility)."""
        if level and level != "INFO":
            formatted_text = f"[{level}] {text}"
        else:
            formatted_text = text
        self.appendLog(formatted_text)

    def appendTaskLog(self, task_id: str, message: str, icon: str = "") -> None:
        """Append task-specific log (for multi-task operations)."""
        if icon:
            formatted_text = f"{icon} [{task_id}] {message}"
        else:
            formatted_text = f"[{task_id}] {message}"
        self.appendLog(formatted_text)

    def appendMultiTaskSummary(self, successful: int, failed: int, total: int) -> None:
        """Append multi-task summary."""
        success_rate = (successful / total * 100) if total > 0 else 0
        if self.translator:
            t = self.translator.t
            summary = t(
                "multi_task_summary",
                successful=successful,
                failed=failed,
                total=total,
                success_rate=f"{success_rate:.1f}",
            )
        else:
            summary = f"Multi-task completed: {successful} successful, {failed} failed, {total} total, 📈 成功率: {success_rate:.1f}%"
        self.appendLog(summary)

    def getLogContent(self) -> str:
        """Get current log content."""
        return self.log_text.toPlainText()

    def setLogContent(self, content: str) -> None:
        """Set log content."""
        self.log_text.setPlainText(content)

    def clearLog(self) -> None:
        """Clear log content."""
        self.log_text.clear()

    def setEnabled(self, enabled: bool) -> None:
        """Set enabled state."""
        super().setEnabled(enabled)
        self.log_text.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.copy_btn.setEnabled(enabled)

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        self.clear_btn.setText(t("log_clear"))
        self.copy_btn.setText(t("log_copy"))
        self.log_text.setPlaceholderText(t("log_placeholder"))

    def get_config(self) -> dict:
        """Get current component configuration."""
        return {
            "log_content": self.getLogContent(),
            "max_lines": 1000,  # Default max lines
        }

    def set_config(self, config: dict) -> None:
        """Set component configuration."""
        if "log_content" in config:
            self.setLogContent(config["log_content"])
