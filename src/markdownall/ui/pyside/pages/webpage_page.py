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
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


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

        # Add rows to the options container
        options_layout.addLayout(row1_layout)
        options_layout.addLayout(row2_layout)
        options_layout.addLayout(row3_layout)

        layout.addWidget(options_frame)

        # Add stretch to center the options
        layout.addStretch(1)

    def _connect_signals(self):
        """Connect checkbox signals."""
        self.use_proxy_cb.stateChanged.connect(self._on_option_changed)
        self.ignore_ssl_cb.stateChanged.connect(self._on_option_changed)
        self.download_images_cb.stateChanged.connect(self._on_option_changed)
        self.filter_site_chrome_cb.stateChanged.connect(self._on_option_changed)
        self.use_shared_browser_cb.stateChanged.connect(self._on_option_changed)

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

    def get_config(self) -> dict:
        """Get current page configuration."""
        return self.get_options()

    def set_config(self, config: dict) -> None:
        """Set page configuration."""
        self.set_options(config)
