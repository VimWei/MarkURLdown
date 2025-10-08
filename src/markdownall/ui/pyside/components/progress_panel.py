"""
Progress Panel Component for MarkdownAll GUI.

This component handles progress display for multi-task operations.
Based on the ProgressPanel_Design.md specification, adapted for MarkdownAll's multi-task features.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class ProgressPanel(QWidget):
    """
    Progress panel component for multi-task progress display.

    This component contains:
    - Progress bar for overall task progress
    - Status label for current processing status
    - Fixed height: 100px
    - Simplified display, detailed info through LogPanel
    """

    # Progress update signal
    progressUpdated = Signal(int, str)  # value, text

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator

        # Set fixed height (adapted for multi-task display)
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout for progress panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(24)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        self.progress.setStyleSheet(
            """
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
        """
        )
        layout.addWidget(self.progress)

        # Simplified status display (single line layout, working with LogPanel)
        self.status_label = QLabel("Ready", self)
        self.status_label.setStyleSheet("color: #555; font-size: 10pt; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def setProgress(self, value: int, text: str = "") -> None:
        """Set progress value and display text."""
        self.progress.setValue(max(0, min(100, int(value))))

        if text:
            # Show custom text
            self.progress.setFormat(text)
        else:
            # Show percentage
            self.progress.setFormat("%p%")

    def setStatus(self, text: str) -> None:
        """Set status text."""
        self.status_label.setText(text)

    def setMultiTaskProgress(
        self,
        current: int,
        total: int,
        current_url: str = "",
        successful: int = 0,
        failed: int = 0,
        pending: int = 0,
    ) -> None:
        """Set multi-task progress (optimized for MarkdownAll)."""
        # Calculate overall progress
        progress = int((current / total) * 100) if total > 0 else 0
        self.setProgress(progress)

        # Set status text (simplified display)
        if current_url:
            self.setStatus(f"Processing {current}/{total}: {current_url}")
        else:
            self.setStatus(f"Processing {current}/{total} URLs")

        # Detailed status information through LogPanel, here only show core progress info

    def reset(self) -> None:
        """Reset progress."""
        self.progress.setValue(0)
        self.progress.setFormat("Ready")
        self.setStatus("Ready")

    def setEnabled(self, enabled: bool) -> None:
        """Set enabled state."""
        super().setEnabled(enabled)
        self.progress.setEnabled(enabled)
        self.status_label.setEnabled(enabled)

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        # Note: These translations may need to be added to the locale files
        # For now, using English labels
        pass

    def get_config(self) -> dict:
        """Get current component configuration."""
        return {
            "progress_value": self.progress.value(),
            "progress_format": self.progress.format(),
            "status_text": self.status_label.text(),
        }

    def set_config(self, config: dict) -> None:
        """Set component configuration."""
        if "progress_value" in config:
            self.progress.setValue(config["progress_value"])
        if "progress_format" in config:
            self.progress.setFormat(config["progress_format"])
        if "status_text" in config:
            self.status_label.setText(config["status_text"])
