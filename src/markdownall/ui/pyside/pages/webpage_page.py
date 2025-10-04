"""
Webpage Page for MarkdownAll GUI.

This page handles conversion options configuration.
It contains all the conversion-related checkboxes and options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
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

    def _setup_ui(self):
        """Setup the UI layout for webpage page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Options frame
        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setSpacing(20)
        options_layout.setContentsMargins(0, 8, 0, 8)
        options_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        # Add checkboxes to layout
        for cb in [
            self.use_proxy_cb,
            self.ignore_ssl_cb,
            self.download_images_cb,
            self.filter_site_chrome_cb,
            self.use_shared_browser_cb,
        ]:
            options_layout.addWidget(cb)

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
