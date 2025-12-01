"""
Webpage Page for MarkdownAll GUI.

This page handles conversion options configuration.
It contains all the conversion-related checkboxes and options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from markdownall.core.registry import GENERIC_HANDLER_NAME, list_handler_names

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


HANDLER_LABEL_KEYS = {
    "WeixinHandler": "handler_option_weixin",
    "ZhihuHandler": "handler_option_zhihu",
    "WordPressHandler": "handler_option_wordpress",
    "NextJSHandler": "handler_option_nextjs",
    "SspaiHandler": "handler_option_sspai",
    "AppinnHandler": "handler_option_appinn",
}


class WebpagePage(QWidget):
    """
    Webpage options configuration page.

    This page contains:
    - Use proxy checkbox
    - Ignore SSL checkbox
    - Download images checkbox
    - Filter site Chrome checkbox
    - Use shared browser checkbox
    """

    # Signals for communicating with MainWindow
    optionsChanged = Signal(dict)

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator

        # Initialize default options
        self.use_proxy_var = False
        self.ignore_ssl_var = False
        self.download_images_var = True
        self.filter_site_chrome_var = True
        self.use_shared_browser_var = True
        self.handler_override = None
        self._available_handlers = list_handler_names()

        # Setup UI
        self._setup_ui()
        self._connect_signals()

        # Debounce timer for coalescing rapid option changes
        self._options_changed_timer = QTimer(self)
        self._options_changed_timer.setSingleShot(True)
        # Short delay to allow multiple checkbox updates to coalesce
        self._options_changed_timer.setInterval(50)
        self._options_changed_timer.timeout.connect(self._emit_options_changed)

    def _setup_ui(self):
        """Setup the UI layout for webpage page."""
        layout = QVBoxLayout(self)
        # Tighter margins/spacing to match MdxScraper
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Options frame
        options_frame = QFrame()
        # Arrange options in three rows
        options_layout = QVBoxLayout(options_frame)
        options_layout.setSpacing(8)
        options_layout.setContentsMargins(0, 6, 0, 6)

        # Create checkboxes
        self.use_proxy_cb = QCheckBox()
        self.use_proxy_cb.setChecked(self.use_proxy_var)

        self.ignore_ssl_cb = QCheckBox()
        self.ignore_ssl_cb.setChecked(self.ignore_ssl_var)

        self.download_images_cb = QCheckBox()
        self.download_images_cb.setChecked(self.download_images_var)

        self.filter_site_chrome_cb = QCheckBox()
        self.filter_site_chrome_cb.setChecked(self.filter_site_chrome_var)

        self.use_shared_browser_cb = QCheckBox()
        self.use_shared_browser_cb.setChecked(self.use_shared_browser_var)

        self.handler_label = QLabel()
        self.handler_combo = QComboBox()
        self.handler_combo.setEditable(False)

        # Row 1: Use system proxy + Ignore SSL verification
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        row1_layout.addWidget(self.use_proxy_cb)
        row1_layout.addWidget(self.ignore_ssl_cb)
        row1_layout.addStretch(1)

        # Row 2: Download images + Filter non-content elements
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)
        row2_layout.addWidget(self.download_images_cb)
        row2_layout.addWidget(self.filter_site_chrome_cb)
        row2_layout.addStretch(1)

        # Row 3: Speed mode (shared browser)
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(10)
        row3_layout.addWidget(self.use_shared_browser_cb)
        row3_layout.addStretch(1)

        # Row 4: Handler override
        row4_layout = QHBoxLayout()
        row4_layout.setSpacing(10)
        row4_layout.addWidget(self.handler_label)
        row4_layout.addWidget(self.handler_combo, 1)
        row4_layout.addStretch(1)

        # Add rows to the options container
        options_layout.addLayout(row1_layout)
        options_layout.addLayout(row2_layout)
        options_layout.addLayout(row3_layout)
        options_layout.addLayout(row4_layout)

        layout.addWidget(options_frame)

        # Add stretch to center the options
        layout.addStretch(1)

        self._rebuild_handler_combo()

    def _connect_signals(self):
        """Connect checkbox signals."""
        self.use_proxy_cb.stateChanged.connect(self._on_option_changed)
        self.ignore_ssl_cb.stateChanged.connect(self._on_option_changed)
        self.download_images_cb.stateChanged.connect(self._on_option_changed)
        self.filter_site_chrome_cb.stateChanged.connect(self._on_option_changed)
        self.use_shared_browser_cb.stateChanged.connect(self._on_option_changed)
        self.handler_combo.currentIndexChanged.connect(self._on_option_changed)

    def _on_option_changed(self):
        """Handle option changes and emit signal."""
        # Start/restart debounce timer to merge multiple changes
        if self._options_changed_timer.isActive():
            self._options_changed_timer.stop()
        self._options_changed_timer.start()

    def _emit_options_changed(self) -> None:
        """Emit optionsChanged once after debounced changes."""
        options = self.get_options()
        self.optionsChanged.emit(options)

    # Public API methods
    def get_options(self) -> dict:
        """Get current conversion options."""
        return {
            "use_proxy": self.use_proxy_cb.isChecked(),
            "ignore_ssl": self.ignore_ssl_cb.isChecked(),
            "download_images": self.download_images_cb.isChecked(),
            "filter_site_chrome": self.filter_site_chrome_cb.isChecked(),
            "use_shared_browser": self.use_shared_browser_cb.isChecked(),
            "handler_override": self._current_handler_override(),
        }

    def set_options(self, options: dict) -> None:
        """Set conversion options."""
        if "use_proxy" in options:
            self.use_proxy_cb.setChecked(bool(options["use_proxy"]))
        if "ignore_ssl" in options:
            self.ignore_ssl_cb.setChecked(bool(options["ignore_ssl"]))
        if "download_images" in options:
            self.download_images_cb.setChecked(bool(options["download_images"]))
        if "filter_site_chrome" in options:
            self.filter_site_chrome_cb.setChecked(bool(options["filter_site_chrome"]))
        if "use_shared_browser" in options:
            self.use_shared_browser_cb.setChecked(bool(options["use_shared_browser"]))
        if "handler_override" in options:
            self._set_handler_override(options.get("handler_override"))

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        self.use_proxy_cb.setText(t("use_proxy_checkbox"))
        self.ignore_ssl_cb.setText(t("ignore_ssl_checkbox"))
        self.download_images_cb.setText(t("download_images_checkbox"))
        self.filter_site_chrome_cb.setText(t("filter_site_chrome_checkbox"))
        self.use_shared_browser_cb.setText(t("use_shared_browser_checkbox"))
        self.handler_label.setText(t("handler_selector_label"))
        self._rebuild_handler_combo()

    def get_config(self) -> dict:
        """Get current page configuration."""
        return self.get_options()

    def set_config(self, config: dict) -> None:
        """Set page configuration."""
        self.set_options(config)

    def _translate(self, key: str, default: str | None = None, **kwargs) -> str:
        if self.translator:
            text = self.translator.t(key, **kwargs)
            if text:
                return text
        return default or key

    def _handler_label_for(self, handler_name: str) -> str:
        key = HANDLER_LABEL_KEYS.get(handler_name)
        if key:
            return self._translate(key, handler_name)
        return handler_name

    def _current_handler_override(self) -> str | None:
        value = self.handler_combo.currentData()
        return value or None

    def _set_handler_override(self, value: str | None):
        target = value or ""
        idx = self.handler_combo.findData(target)
        if idx < 0:
            idx = 0
        self.handler_combo.setCurrentIndex(idx)

    def _rebuild_handler_combo(self):
        current_value = self.handler_combo.currentData()
        block = self.handler_combo.blockSignals(True)
        self.handler_combo.clear()
        # Auto option
        self.handler_combo.addItem(self._translate("handler_option_auto", "Auto"), "")
        # Generic fallback
        self.handler_combo.addItem(
            self._translate("handler_option_generic", "Generic"), GENERIC_HANDLER_NAME
        )
        for handler_name in self._available_handlers:
            self.handler_combo.addItem(self._handler_label_for(handler_name), handler_name)
        if current_value is not None:
            idx = self.handler_combo.findData(current_value)
            if idx >= 0:
                self.handler_combo.setCurrentIndex(idx)
        else:
            self.handler_combo.setCurrentIndex(0)
        self.handler_combo.blockSignals(block)
