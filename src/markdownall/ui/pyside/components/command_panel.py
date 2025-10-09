"""
Command Panel Component for MarkdownAll GUI.

This component handles session management and conversion control.
Based on the CommandPanel_Design.md specification, mimicking MdxScraper's design.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class CommandPanel(QWidget):
    """
    Command panel component for session management and conversion control.

    This component contains:
    - Session management buttons (restore, import, export)
    - Conversion control button (convert/stop)
    - Progress bar display
    - Fixed height: 120px
    """

    # Session management signals
    restoreRequested = Signal()
    importRequested = Signal()
    exportRequested = Signal()
    # Conversion control signals
    convertRequested = Signal()
    stopRequested = Signal()

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator
        self._is_converting = False
        self._ready_text = "Ready"

        # Set fixed height for command panel (mimicking MdxScraper)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Setup UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the UI layout for command panel."""
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

        row_actions.addWidget(self.btn_restore)
        row_actions.addSpacing(12)
        row_actions.addWidget(self.btn_import)
        row_actions.addSpacing(12)
        row_actions.addWidget(self.btn_export)
        row_actions.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(row_actions)

        # Row 2: convert/stop (centered)
        row_convert = QHBoxLayout()
        row_convert.setContentsMargins(0, 0, 0, 0)
        row_convert.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.btn_convert = QPushButton("Convert to Markdown", self)
        self.btn_convert.setFixedWidth(200)
        self.btn_convert.setFixedHeight(40)
        self.btn_convert.setObjectName("convert-button")
        # Use a dynamic property to toggle visual style for stop state
        self.btn_convert.setProperty("mode", "convert")

        row_convert.addWidget(self.btn_convert)
        row_convert.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        root.addLayout(row_convert)

        # Progress (simplified, detailed progress in ProgressPanel)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(20)
        self.progress.setTextVisible(True)  # Show text like MdxScraper
        # Initial status text (localized if possible)
        if self.translator:
            self._ready_text = self.translator.t("progress_ready")
        self.progress.setFormat(self._ready_text)
        root.addWidget(self.progress)

    def _connect_signals(self):
        """Connect internal signals."""
        self.btn_restore.clicked.connect(self.restoreRequested.emit)
        self.btn_import.clicked.connect(self.importRequested.emit)
        self.btn_export.clicked.connect(self.exportRequested.emit)
        self.btn_convert.clicked.connect(self._on_convert_clicked)

    def _on_convert_clicked(self) -> None:
        """Toggle convert/stop by internal converting state."""
        if self._is_converting:
            self.stopRequested.emit()
        else:
            self.convertRequested.emit()

    # Public API (mimicking MdxScraper)
    def setProgress(self, value: int) -> None:
        """Set progress value."""
        self.progress.setValue(max(0, min(100, int(value))))
        # Only show percentage if no custom status text is set
        current_format = self.progress.format()
        if current_format in (self._ready_text, "%p%"):
            self.progress.setFormat("%p%")

    def set_progress(self, value: int, text: str = None) -> None:
        """Set progress value and optional text (for compatibility)."""
        self.setProgress(value)
        if text:
            self.setProgressText(text)

    def setProgressText(self, text: str) -> None:
        """Set progress bar display text."""
        self.progress.setFormat(text)

    def setConvertButtonText(self, text: str) -> None:
        """Set convert button text (for convert/stop state switching)."""
        self.btn_convert.setText(text)

    def setConvertingState(self, is_converting: bool) -> None:
        """Set converting state (single button toggles text and style)."""
        self._is_converting = bool(is_converting)
        # Update text
        if self.translator:
            t = self.translator.t
            self.btn_convert.setText(
                t("command_stop") if self._is_converting else t("command_convert")
            )
        else:
            self.btn_convert.setText("Stop" if self._is_converting else "Convert to Markdown")
        # Update style via dynamic property
        self.btn_convert.setProperty("mode", "stop" if self._is_converting else "convert")
        # Force style refresh so QSS picks up property change
        style = self.btn_convert.style()
        style.unpolish(self.btn_convert)
        style.polish(self.btn_convert)
        self.btn_convert.update()

    def setEnabled(self, enabled: bool) -> None:
        """Set enabled state."""
        super().setEnabled(enabled)
        # Keep buttons consistent when disabling panel
        for b in (self.btn_restore, self.btn_import, self.btn_export, self.btn_convert):
            b.setEnabled(enabled)

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        self.btn_restore.setText(t("command_restore_config"))
        self.btn_import.setText(t("command_import_config"))
        self.btn_export.setText(t("command_export_config"))
        # Update ready text and apply when idle at 0
        old_ready = self._ready_text
        self._ready_text = t("progress_ready")
        if not self._is_converting and self.progress.value() == 0:
            self.progress.setFormat(self._ready_text)
        # Keep current state text
        if self._is_converting:
            self.btn_convert.setText(t("command_stop"))
        else:
            self.btn_convert.setText(t("command_convert"))

    def get_config(self) -> dict:
        """Get current component configuration."""
        return {
            "convert_button_text": self.btn_convert.text(),
            "progress_value": self.progress.value(),
            "progress_format": self.progress.format(),
        }

    def set_config(self, config: dict) -> None:
        """Set component configuration."""
        if "convert_button_text" in config:
            self.btn_convert.setText(config["convert_button_text"])
        if "progress_value" in config:
            self.progress.setValue(config["progress_value"])
        if "progress_format" in config:
            self.progress.setFormat(config["progress_format"])
