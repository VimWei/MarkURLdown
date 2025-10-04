"""
Basic Page for MarkdownAll GUI.

This page handles URL management and output directory configuration.
It contains the core functionality for managing URLs and selecting output directory.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class BasicPage(QWidget):
    """
    Basic configuration page for URL management and output directory.
    
    This page contains:
    - URL input field and add button
    - URL list with management buttons (up, down, delete, clear, copy)
    - Output directory selection
    """
    
    # Signals for communicating with MainWindow
    urlListChanged = Signal(list)
    outputDirChanged = Signal(str)
    addUrlRequested = Signal(str)  # For adding single URL

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator
        
        # Initialize data
        self.output_dir_var = ""
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the UI layout for basic page."""
        layout = QGridLayout(self)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        # Row 0: URL Input
        self.url_label = QLabel()
        layout.addWidget(self.url_label, 0, 0)
        
        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.url_entry, 0, 1, 1, 2)
        
        button_height = self.url_entry.sizeHint().height()
        self.add_btn = QPushButton()
        self.add_btn.setFixedHeight(button_height)
        layout.addWidget(self.add_btn, 0, 3)

        # Row 1: URL List
        self.url_list_label = QLabel()
        layout.addWidget(self.url_list_label, 1, 0)
        
        self.url_listbox = QListWidget()
        layout.addWidget(self.url_listbox, 1, 1, 1, 2)
        
        # URL management buttons
        url_btn_frame = QFrame()
        url_btn_layout = QVBoxLayout(url_btn_frame)
        url_btn_layout.setSpacing(2)
        url_btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.move_up_btn = QPushButton()
        self.move_down_btn = QPushButton()
        self.copy_btn = QPushButton()
        self.delete_btn = QPushButton()
        self.clear_btn = QPushButton()
        
        for btn in [
            self.move_up_btn,
            self.move_down_btn,
            self.copy_btn,
            self.delete_btn,
            self.clear_btn,
        ]:
            btn.setFixedHeight(button_height)
            url_btn_layout.addWidget(btn)
        
        layout.addWidget(url_btn_frame, 1, 3)

        # Row 2: Output Directory
        self.output_dir_label = QLabel()
        layout.addWidget(self.output_dir_label, 2, 0)
        
        self.output_entry = QLineEdit(self.output_dir_var)
        self.output_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.output_entry, 2, 1, 1, 2)
        
        self.choose_dir_btn = QPushButton()
        self.choose_dir_btn.setFixedHeight(button_height)
        layout.addWidget(self.choose_dir_btn, 2, 3)

        # Layout stretching
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(1, 1)
        
        # Set focus to URL entry
        self.url_entry.setFocus()

    def _connect_signals(self):
        """Connect internal signals."""
        self.add_btn.clicked.connect(self._add_url_from_entry)
        self.move_up_btn.clicked.connect(self._move_selected_up)
        self.move_down_btn.clicked.connect(self._move_selected_down)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_btn.clicked.connect(self._clear_list)
        self.copy_btn.clicked.connect(self._copy_selected)
        self.choose_dir_btn.clicked.connect(self._choose_output_dir)
        self.url_entry.returnPressed.connect(self._add_url_from_entry)
        
        # Connect output directory changes
        self.output_entry.textChanged.connect(self._on_output_dir_changed)

    def _add_url_from_entry(self):
        """Add URL(s) from the input field."""
        raw = self.url_entry.text().strip()
        if not raw:
            return
            
        parts = [p.strip() for p in raw.replace("\r", "\n").split("\n")]
        urls = []
        
        for part in parts:
            if not part:
                continue
            for token in part.split():
                u = token.strip()
                if not u:
                    continue
                if not u.lower().startswith(("http://", "https://")):
                    u = "https://" + u
                urls.append(u)
        
        if not urls:
            return
            
        for u in urls:
            self.url_listbox.addItem(u)
            
        self.url_entry.setText("")
        self._emit_url_list_changed()

    def _move_selected_up(self):
        """Move selected URL up in the list."""
        current = self.url_listbox.currentRow()
        if current > 0:
            item = self.url_listbox.takeItem(current)
            self.url_listbox.insertItem(current - 1, item)
            self.url_listbox.setCurrentRow(current - 1)
            self._emit_url_list_changed()

    def _move_selected_down(self):
        """Move selected URL down in the list."""
        current = self.url_listbox.currentRow()
        if current < self.url_listbox.count() - 1:
            item = self.url_listbox.takeItem(current)
            self.url_listbox.insertItem(current + 1, item)
            self.url_listbox.setCurrentRow(current + 1)
            self._emit_url_list_changed()

    def _delete_selected(self):
        """Delete selected URL from the list."""
        current = self.url_listbox.currentRow()
        if current >= 0:
            self.url_listbox.takeItem(current)
            self._emit_url_list_changed()

    def _clear_list(self):
        """Clear all URLs from the list."""
        self.url_listbox.clear()
        self._emit_url_list_changed()

    def _copy_selected(self):
        """Copy selected URL to clipboard."""
        current = self.url_listbox.currentRow()
        if current >= 0:
            url = self.url_listbox.item(current).text()
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            # Emit signal for status update
            self.addUrlRequested.emit(f"URL copied: {url}")

    def _choose_output_dir(self):
        """Open directory chooser dialog."""
        if not self.translator:
            return
            
        chosen = QFileDialog.getExistingDirectory(
            self,
            self.translator.t("dialog_choose_output_dir"),
            self.output_entry.text() or os.getcwd(),
        )
        if chosen:
            self.output_entry.setText(os.path.abspath(chosen))

    def _on_output_dir_changed(self):
        """Handle output directory text change."""
        self.outputDirChanged.emit(self.output_entry.text())

    def _emit_url_list_changed(self):
        """Emit signal when URL list changes."""
        urls = [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())]
        self.urlListChanged.emit(urls)

    # Public API methods
    def get_urls(self) -> list[str]:
        """Get current URL list."""
        return [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())]

    def set_urls(self, urls: list[str]) -> None:
        """Set URL list."""
        self.url_listbox.clear()
        for url in urls:
            self.url_listbox.addItem(url)
        self._emit_url_list_changed()

    def get_output_dir(self) -> str:
        """Get current output directory."""
        return self.output_entry.text()

    def set_output_dir(self, path: str) -> None:
        """Set output directory."""
        self.output_entry.setText(path)

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return
            
        t = self.translator.t
        self.url_label.setText(t("url_label"))
        self.add_btn.setText(t("add_button"))
        self.url_list_label.setText(t("url_list_label"))
        self.move_up_btn.setText(t("move_up_button"))
        self.move_up_btn.setToolTip(t("tooltip_move_up"))
        self.move_down_btn.setText(t("move_down_button"))
        self.move_down_btn.setToolTip(t("tooltip_move_down"))
        self.delete_btn.setText(t("delete_button"))
        self.delete_btn.setToolTip(t("tooltip_delete"))
        self.clear_btn.setText(t("clear_button"))
        self.clear_btn.setToolTip(t("tooltip_clear"))
        self.copy_btn.setText(t("copy_button"))
        self.copy_btn.setToolTip(t("tooltip_copy"))
        self.output_dir_label.setText(t("output_dir_label"))
        self.choose_dir_btn.setText(t("choose_dir_button"))

    def get_config(self) -> dict:
        """Get current page configuration."""
        return {
            "urls": self.get_urls(),
            "output_dir": self.get_output_dir(),
        }

    def set_config(self, config: dict) -> None:
        """Set page configuration."""
        if "urls" in config:
            self.set_urls(config["urls"])
        if "output_dir" in config:
            self.set_output_dir(config["output_dir"])
