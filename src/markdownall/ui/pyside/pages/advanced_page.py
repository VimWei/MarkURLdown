"""
Advanced Page for MarkdownAll GUI.

This page handles advanced configuration and system management.
Based on the Advanced_Page_Design.md specification.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class AdvancedPage(QWidget):
    """
    Advanced options configuration page.

    This page contains:
    - User data directory management
    - Configuration operations
    - System settings (debug mode, language)
    """

    # Signals for communicating with MainWindow
    openUserDataRequested = Signal()
    restoreDefaultConfigRequested = Signal()
    debugModeChanged = Signal(bool)
    languageChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator

        # Initialize data
        self.user_data_path = ""
        self.language = "auto"
        self.debug_mode = False
        # Track whether data path field shows the localized hint text
        self._is_data_path_hint = True

        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_data_path()

    def _setup_ui(self):
        """Setup the UI layout for advanced page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # User Data Path section (mirror MdxScraper style)
        data_section = QHBoxLayout()
        self._lbl_data = QLabel("", self)
        self._lbl_data.setProperty("class", "field-label")
        self._lbl_data.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        data_section.addWidget(self._lbl_data)
        data_section.addSpacing(8)

        self.edit_data_path = QLineEdit(self)
        self.edit_data_path.setReadOnly(True)
        self.edit_data_path.setProperty("class", "readonly-input")
        data_section.addWidget(self.edit_data_path, 1)

        self.btn_open_data = QPushButton("", self)
        self.btn_open_data.setFixedWidth(90)
        self.btn_open_data.setObjectName("open-data-button")
        data_section.addWidget(self.btn_open_data)
        layout.addLayout(data_section)

        # Config Actions section
        config_section = QHBoxLayout()
        self._lbl_config = QLabel("", self)
        self._lbl_config.setProperty("class", "field-label")
        self._lbl_config.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        config_section.addWidget(self._lbl_config)
        config_section.addSpacing(8)

        self.btn_restore_default = QPushButton("", self)
        self.btn_restore_default.setFixedWidth(150)
        self.btn_restore_default.setObjectName("restore-default-button")
        config_section.addWidget(self.btn_restore_default)
        config_section.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(config_section)

        # Language section
        system_section = QHBoxLayout()
        self._lbl_language_left = QLabel("", self)
        self._lbl_language_left.setProperty("class", "field-label")
        self._lbl_language_left.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        system_section.addWidget(self._lbl_language_left)
        system_section.addSpacing(8)

        self.language_combo = QComboBox(self)
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("简体中文", "zh")
        self.language_combo.addItem("Auto", "auto")
        self.language_combo.setCurrentText("Auto")
        self.language_combo.setFixedWidth(100)
        system_section.addWidget(self.language_combo)
        system_section.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(system_section)

        # Align section labels to the longest label width (with padding)
        _section_w = (
            max(
                self._lbl_data.sizeHint().width(),
                self._lbl_config.sizeHint().width(),
                self._lbl_language_left.sizeHint().width(),
            )
            + 16
        )
        self._lbl_data.setFixedWidth(_section_w)
        self._lbl_config.setFixedWidth(_section_w)
        self._lbl_language_left.setFixedWidth(_section_w)

        # Bottom spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Initial translate for created widgets
        try:
            self.retranslate_ui()
        except Exception:
            pass

    def _connect_signals(self):
        """Connect internal widget signals to page signals."""
        self.btn_open_data.clicked.connect(self.openUserDataRequested.emit)
        self.btn_restore_default.clicked.connect(self.restoreDefaultConfigRequested.emit)
        # (Debug Mode removed)
        self.language_combo.currentTextChanged.connect(
            lambda text: self.languageChanged.emit(self.language_combo.currentData())
        )

    def _update_data_path(self):
        """Show user data directory path."""
        # Get the project root from parent and resolve absolute path for internal use
        project_root = self._get_project_root()
        if project_root:
            data_path = os.path.join(project_root, "data")
            self.user_data_path = data_path
        else:
            self.user_data_path = "data/"
        # Display default: show the relative hint. After Open, the field shows the absolute path.
        try:
            if self.translator:
                self.edit_data_path.setText(self.translator.t("advanced_data_path_hint"))
            else:
                self.edit_data_path.setText("data/ (relative to project root)")
        except Exception:
            self.edit_data_path.setText("data/ (relative to project root)")
        # Mark as hint since we show the template text at startup
        self._is_data_path_hint = True

    def _get_project_root(self) -> str | None:
        """Walk up the parent chain to find project root."""
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

    # Public API methods
    def get_user_data_path(self) -> str:
        """Get user data directory path."""
        return self.user_data_path

    def set_user_data_path(self, path: str) -> None:
        """Set user data directory path."""
        self.user_data_path = path
        # Reflect absolute path in the readonly input when explicitly set
        try:
            if hasattr(self, "edit_data_path") and self.edit_data_path is not None:
                self.edit_data_path.setText(path)
                # Now the field displays a concrete absolute path, not the hint
                self._is_data_path_hint = False
        except Exception:
            # Fallback silently if widget not ready
            pass

    def get_language(self) -> str:
        """Get current language setting."""
        return self.language_combo.currentData()

    def set_language(self, lang_code: str) -> None:
        """Set language setting."""
        index = self.language_combo.findData(lang_code)
        if index != -1:
            self.language_combo.setCurrentIndex(index)

    # Debug mode removed

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        # Update internal labels and buttons
        try:
            self._lbl_data.setText(t("advanced_user_data_path"))
            self._lbl_config.setText(t("advanced_config_actions"))
            self._lbl_language_left.setText(t("advanced_language"))
            self.btn_open_data.setText(t("advanced_open_data"))
            self.btn_restore_default.setText(t("advanced_restore_default"))
            # If currently showing the hint, refresh it in the new language
            if getattr(self, "_is_data_path_hint", True):
                self.edit_data_path.setText(t("advanced_data_path_hint"))
        except Exception:
            pass

        # Recompute and apply deterministic label widths based on translated texts
        try:
            metrics = self.fontMetrics()
            left_w = (
                max(
                    metrics.horizontalAdvance(self._lbl_data.text()),
                    metrics.horizontalAdvance(self._lbl_config.text()),
                    metrics.horizontalAdvance(self._lbl_language_left.text()),
                )
                + 16
            )
            self._lbl_data.setFixedWidth(left_w)
            self._lbl_config.setFixedWidth(left_w)
            self._lbl_language_left.setFixedWidth(left_w)
        except Exception:
            pass

        # No dynamic realignment; label width set once during setup

    def get_config(self) -> dict:
        """Get current page configuration."""
        return {
            "user_data_path": self.get_user_data_path(),
            "language": self.get_language(),
            # debug_mode removed
        }

    def set_config(self, config: dict) -> None:
        """Set page configuration."""
        if "user_data_path" in config:
            # Keep internal path only if provided value is non-empty; otherwise keep default
            val = config["user_data_path"]
            if isinstance(val, str) and val.strip():
                self.user_data_path = val.strip()
        # Always display the relative hint for consistency with MdxScraper
        try:
            if self.translator:
                self.edit_data_path.setText(self.translator.t("advanced_data_path_hint"))
            else:
                self.edit_data_path.setText("data/ (relative to project root)")
        except Exception:
            self.edit_data_path.setText("data/ (relative to project root)")
        # Mark as hint since we deliberately display the template text here
        self._is_data_path_hint = True
        if "language" in config:
            self.set_language(config["language"])
        # debug_mode removed

    # Dynamic re-alignment removed; stable layout mirrors MdxScraper
