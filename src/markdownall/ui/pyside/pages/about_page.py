"""
About Page for MarkdownAll GUI.

This page handles project homepage and version check functionality.
Based on the About_Page_Design.md specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from markdownall.services.version_check_service import VersionCheckService

if TYPE_CHECKING:
    from markdownall.ui.pyside.main_window import Translator


class VersionCheckThread(QThread):
    """Thread for checking version updates without blocking UI."""

    update_available = Signal(bool, str, str)  # is_latest, message, latest_version

    def __init__(self):
        super().__init__()
        self.version_service = VersionCheckService()

    def run(self):
        """Run version check in background thread."""
        is_latest, message, latest_version = self.version_service.check_for_updates()
        self.update_available.emit(is_latest, message, latest_version or "")


class AboutPage(QWidget):
    """
    About page for project information and version checking.

    This page contains:
    - Project homepage link
    - Version check functionality
    """

    # Signals for communicating with MainWindow
    checkUpdatesRequested = Signal()
    openHomepageRequested = Signal()

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
        super().__init__(parent)
        self.translator = translator

        # Initialize version check thread
        self.version_thread = None

        # Setup UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the UI layout for about page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Row: Homepage (mirror MdxScraper)
        home_row = QHBoxLayout()
        self._lbl_home = QLabel("", self)
        self._lbl_home.setProperty("class", "field-label")
        self._lbl_home.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._lbl_home.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        home_row.addWidget(self._lbl_home)
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

        # Row: Updates (mirror MdxScraper)
        update_row = QHBoxLayout()
        self._lbl_update = QLabel("", self)
        self._lbl_update.setProperty("class", "field-label")
        self._lbl_update.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._lbl_update.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        update_row.addWidget(self._lbl_update)
        update_row.addSpacing(8)

        self.update_status_label = QLabel("", self)
        self.update_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.update_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        update_row.addWidget(self.update_status_label, 1)

        self.check_updates_btn = QPushButton("", self)
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        self.check_updates_btn.setFixedWidth(120)
        self.check_updates_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        update_row.addWidget(self.check_updates_btn)

        layout.addLayout(update_row)

        # Align left labels to longest width with padding
        _section_w = (
            max(self._lbl_home.sizeHint().width(), self._lbl_update.sizeHint().width()) + 16
        )
        self._lbl_home.setFixedWidth(_section_w)
        self._lbl_update.setFixedWidth(_section_w)

        layout.addStretch(1)

        # Initial translate
        try:
            self.retranslate_ui()
        except Exception:
            # Fallback to English if translation fails
            self._lbl_home.setText("Homepage:")
            self._lbl_update.setText("Updates:")
            self.update_status_label.setText("Click 'Check for Updates' to check")
            self.check_updates_btn.setText("Check for Updates")

    def _connect_signals(self):
        """Connect internal signals."""
        # Signals are already connected in _setup_ui
        pass

    def check_for_updates(self):
        """Start checking for updates in background thread."""
        if self.version_thread and self.version_thread.isRunning():
            return  # Already checking

        # Update UI to show checking status
        if self.translator:
            self.update_status_label.setText(self.translator.t("about_checking"))
        else:
            self.update_status_label.setText("Checking for updates...")
        self.check_updates_btn.setEnabled(False)
        if self.translator:
            self.check_updates_btn.setText(self.translator.t("about_checking"))
        else:
            self.check_updates_btn.setText("Checking...")

        # Create and start version check thread
        self.version_thread = VersionCheckThread()
        self.version_thread.update_available.connect(self.on_update_check_complete)
        self.version_thread.finished.connect(self.on_version_thread_finished)
        self.version_thread.start()

    def on_update_check_complete(self, is_latest: bool, message: str, latest_version: str):
        """Handle update check completion."""
        # Map English messages to translation keys for localization
        if self.translator:
            try:
                if message == "You are using the latest version.":
                    self.update_status_label.setText(self.translator.t("about_latest_version"))
                elif message.startswith("New version") and "available" in message:
                    # Extract version from message and format with translation
                    version = latest_version or "unknown"
                    self.update_status_label.setText(self.translator.t("about_new_version_available").format(version=version))
                elif "Failed to check for updates" in message and "internet connection" in message:
                    self.update_status_label.setText(self.translator.t("about_check_failed"))
                elif "Failed to parse update information" in message:
                    self.update_status_label.setText(self.translator.t("about_parse_failed"))
                elif "An error occurred while checking for updates" in message:
                    self.update_status_label.setText(self.translator.t("about_check_error"))
                else:
                    self.update_status_label.setText(message)
            except Exception:
                self.update_status_label.setText(message)
        else:
            self.update_status_label.setText(message)

        # Update button text based on result
        if self.translator:
            self.check_updates_btn.setText(self.translator.t("about_check_again"))
        else:
            self.check_updates_btn.setText("Check Again")

    def on_version_thread_finished(self):
        """Handle version check thread completion."""
        self.check_updates_btn.setEnabled(True)
        if self.translator:
            self.check_updates_btn.setText(self.translator.t("about_check_again"))
        else:
            self.check_updates_btn.setText("Check Again")
        if self.version_thread:
            self.version_thread.deleteLater()
            self.version_thread = None

    def retranslate_ui(self):
        """Retranslate UI elements."""
        if not self.translator:
            return

        t = self.translator.t
        try:
            self._lbl_home.setText(t("about_homepage"))
            self._lbl_update.setText(t("about_updates"))
            # Only text values; widths fixed at setup
            # Set default message text to hint user
            self.update_status_label.setText(t("about_click_to_check"))
            self.check_updates_btn.setText(t("about_check_updates"))
        except Exception:
            pass

        # Recompute and apply deterministic label widths after translation
        try:
            metrics = self.fontMetrics()
            left_w = (
                max(
                    metrics.horizontalAdvance(self._lbl_home.text()),
                    metrics.horizontalAdvance(self._lbl_update.text()),
                )
                + 16
            )
            self._lbl_home.setFixedWidth(left_w)
            self._lbl_update.setFixedWidth(left_w)
        except Exception:
            pass

    # Dynamic label realignment removed; using stable form layout

    def get_config(self) -> dict:
        """Get current configuration from the page."""
        return {
            "homepage_clicked": getattr(self, "_homepage_clicked", False),
            "last_update_check": getattr(self, "_last_update_check", None),
        }

    def set_config(self, config: dict) -> None:
        """Set configuration for the page."""
        if "homepage_clicked" in config:
            self._homepage_clicked = config["homepage_clicked"]
        if "last_update_check" in config:
            self._last_update_check = config["last_update_check"]
