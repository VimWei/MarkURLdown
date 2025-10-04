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
    - System settings (log level, debug mode, language)
    """
    
    # Signals for communicating with MainWindow
    openUserDataRequested = Signal()
    restoreDefaultConfigRequested = Signal()
    logLevelChanged = Signal(str)
    debugModeChanged = Signal(bool)
    languageChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator
        
        # Initialize data
        self.user_data_path = ""
        self.language = "auto"
        self.log_level = "INFO"
        self.debug_mode = False
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_data_path()

    def _setup_ui(self):
        """Setup the UI layout for advanced page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # User data directory section
        data_section = QHBoxLayout()
        _lbl_data = QLabel("User Data Path:", self)
        _lbl_data.setProperty("class", "field-label")
        _lbl_data.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        data_section.addWidget(_lbl_data)
        data_section.addSpacing(8)

        self.edit_data_path = QLineEdit(self)
        self.edit_data_path.setReadOnly(True)
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

        # System settings section
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
        self.log_level_combo.setCurrentText(self.log_level)
        self.log_level_combo.setFixedWidth(100)
        log_level_frame.addWidget(log_level_label)
        log_level_frame.addWidget(self.log_level_combo)

        # Debug mode checkbox
        self.debug_mode_cb = QCheckBox("Debug Mode", self)
        self.debug_mode_cb.setChecked(self.debug_mode)

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

    def _connect_signals(self):
        """Connect internal widget signals to page signals."""
        self.btn_open_data.clicked.connect(self.openUserDataRequested.emit)
        self.btn_restore_default.clicked.connect(self.restoreDefaultConfigRequested.emit)
        self.log_level_combo.currentTextChanged.connect(self.logLevelChanged.emit)
        self.debug_mode_cb.stateChanged.connect(
            lambda checked: self.debugModeChanged.emit(bool(checked))
        )
        self.language_combo.currentTextChanged.connect(
            lambda text: self.languageChanged.emit(self.language_combo.currentData())
        )

    def _update_data_path(self):
        """Show user data directory path."""
        # Get the project root from parent
        project_root = self._get_project_root()
        if project_root:
            data_path = os.path.join(project_root, "data")
            self.edit_data_path.setText(data_path)
            self.user_data_path = data_path
        else:
            self.edit_data_path.setText("data/ (relative to project root)")
            self.user_data_path = "data/"

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

    def get_language(self) -> str:
        """Get current language setting."""
        return self.language_combo.currentData()

    def set_language(self, lang_code: str) -> None:
        """Set language setting."""
        index = self.language_combo.findData(lang_code)
        if index != -1:
            self.language_combo.setCurrentIndex(index)

    def get_log_level(self) -> str:
        """Get current log level."""
        return self.log_level_combo.currentText()

    def set_log_level(self, level: str) -> None:
        """Set log level."""
        self.log_level_combo.setCurrentText(level)

    def get_debug_mode(self) -> bool:
        """Get debug mode setting."""
        return self.debug_mode_cb.isChecked()

    def set_debug_mode(self, enabled: bool) -> None:
        """Set debug mode."""
        self.debug_mode_cb.setChecked(enabled)

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return
            
        t = self.translator.t
        # Update labels - check if parent has tabs attribute
        try:
            parent = self.parent()
            if hasattr(parent, 'tabs') and parent.tabs:
                for i in range(parent.tabs.count()):
                    if parent.tabs.widget(i) == self:
                        if i == 0:
                            parent.tabs.setTabText(i, t("tab_basic"))
                        elif i == 1:
                            parent.tabs.setTabText(i, t("tab_webpage"))
                        elif i == 2:
                            parent.tabs.setTabText(i, t("tab_advanced"))
                        elif i == 3:
                            parent.tabs.setTabText(i, t("tab_about"))
                        break
        except (AttributeError, TypeError):
            # Parent doesn't have tabs or is not the expected type
            pass

    def get_config(self) -> dict:
        """Get current page configuration."""
        return {
            "user_data_path": self.get_user_data_path(),
            "language": self.get_language(),
            "log_level": self.get_log_level(),
            "debug_mode": self.get_debug_mode(),
        }

    def set_config(self, config: dict) -> None:
        """Set page configuration."""
        if "user_data_path" in config:
            self.user_data_path = config["user_data_path"]
            self.edit_data_path.setText(config["user_data_path"])
        if "language" in config:
            self.set_language(config["language"])
        if "log_level" in config:
            self.set_log_level(config["log_level"])
        if "debug_mode" in config:
            self.set_debug_mode(config["debug_mode"])
