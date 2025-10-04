"""
Main Window for MarkdownAll GUI Refactor.

This module implements the new modular main window design based on MdxScraper's
successful architecture while preserving MarkdownAll's unique features.
"""

from __future__ import annotations

import json
import locale
import os
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QClipboard, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QWidget,
)

from markdownall.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markdownall.io.config import (
    load_config,
    load_json_from_root,
    resolve_project_path,
    save_config,
    to_project_relative_path,
)
from markdownall.ui.pyside.splash import show_immediate_splash
from markdownall.ui.viewmodel import ViewModel
from markdownall.version import get_app_title

# Import pages and components
from .pages import BasicPage, WebpagePage, AdvancedPage, AboutPage
from .components import CommandPanel, ProgressPanel, LogPanel


class Translator:
    """Translation system for MarkdownAll GUI."""
    
    def __init__(self, locales_dir: str):
        self.locales_dir = locales_dir
        self.translations = {}

    def load_language(self, lang_code: str):
        """Load language translations."""
        if lang_code == "auto":
            lang_code, _ = locale.getdefaultlocale()
            lang_code = lang_code.split("_")[0] if lang_code else "en"

        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")

        if not os.path.exists(file_path):
            lang_code = "en"
            file_path = os.path.join(self.locales_dir, "en.json")

        with open(file_path, "r", encoding="utf-8") as f:
            self.translations = json.load(f)
        self.language = lang_code

    def t(self, key: str, **kwargs) -> str:
        """Translate text with optional formatting."""
        text = self.translations.get(key, key)
        return text.format(**kwargs)


class ProgressSignals(QObject):
    """Progress event signals for thread-safe UI updates."""
    
    progress_event = Signal(object)

    def __init__(self):
        super().__init__()


class MainWindow(QMainWindow):
    """
    Main Window for MarkdownAll GUI Refactor.
    
    This class implements the new modular design with:
    - Tabbed interface for different configuration pages
    - Splitter layout for responsive design
    - Component-based architecture
    - Preserved existing functionality
    """
    
    # Main window signals
    conversionStarted = Signal()
    conversionFinished = Signal()
    conversionProgress = Signal(int, str)  # progress, message
    errorOccurred = Signal(str)
    configChanged = Signal(str, dict)  # config_type, data

    def __init__(self, root_dir: str, settings: dict | None = None):
        super().__init__()
        
        # Initialize basic properties
        settings = settings or {}
        self.root_dir = root_dir
        self.ui_ready = False
        self.is_running = False
        
        # Initialize translation system
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        self.translator = Translator(locales_dir)
        self.current_lang = settings.get("language", "auto")
        self.translator.load_language(self.current_lang)
        
        # Initialize ViewModel and signals (preserve existing architecture)
        self.vm = ViewModel()
        self.signals = ProgressSignals()
        
        # Default configuration (preserve existing defaults)
        self.output_dir_var = os.path.abspath(os.path.join(root_dir, "data", "output"))
        self.use_proxy_var = False
        self.ignore_ssl_var = False
        self.download_images_var = True
        self.filter_site_chrome_var = True
        self.use_shared_browser_var = True
        
        # Setup UI components
        self._setup_ui()
        self._retranslate_ui()
        self._connect_signals()
        
        # Connect progress signals for thread-safe UI updates
        self.signals.progress_event.connect(self._on_event_thread_safe)
        self.ui_ready = True

    def closeEvent(self, event):
        """Handle window close event with session state saving."""
        try:
            # Save current session state
            state_data = self._get_current_state()
            state_path = os.path.join(self.root_dir, "data", "sessions", "last_state.json")
            save_config(state_path, state_data)
        except Exception as e:
            print(f"Error saving session state on exit: {e}")
        finally:
            event.accept()

    def _setup_ui(self):
        """Setup the main UI layout with tabbed interface and splitter."""
        # Set window properties
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(920, 600)
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.setMinimumSize(800, 520)
        
        # Create central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main splitter (vertical)
        self.splitter = QSplitter(Qt.Vertical, central_widget)
        
        # Setup tabbed interface
        self._setup_tabbed_interface()
        
        # Setup components (will be implemented in phase 2)
        self._setup_components()
        
        # Configure splitter
        self._configure_splitter()

    def _setup_tabbed_interface(self):
        """Setup the tabbed interface with pages."""
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create real pages
        self._create_pages()
        
        # Add tabs to splitter
        self.splitter.addWidget(self.tabs)

    def _create_pages(self):
        """Create real pages with functionality."""
        # Basic Page - URL management and output directory
        self.basic_page = BasicPage(self, self.translator)
        self.tabs.addTab(self.basic_page, "Basic")
        
        # Webpage Page - Conversion options
        self.webpage_page = WebpagePage(self, self.translator)
        self.tabs.addTab(self.webpage_page, "Webpage")
        
        # Advanced Page - Advanced options and system management
        self.advanced_page = AdvancedPage(self, self.translator)
        self.tabs.addTab(self.advanced_page, "Advanced")
        
        # About Page - Project homepage and version check
        self.about_page = AboutPage(self, self.translator)
        self.tabs.addTab(self.about_page, "About")

    def _setup_components(self):
        """Setup components (CommandPanel, ProgressPanel, LogPanel)."""
        # Create CommandPanel - Session management and conversion control
        self.command_panel = CommandPanel(self, self.translator)
        self.splitter.addWidget(self.command_panel)
        
        # Create ProgressPanel - Multi-task progress display
        self.progress_panel = ProgressPanel(self, self.translator)
        self.splitter.addWidget(self.progress_panel)
        
        # Create LogPanel - Detailed log information display
        self.log_panel = LogPanel(self, self.translator)
        self.splitter.addWidget(self.log_panel)

    def _configure_splitter(self):
        """Configure splitter behavior and initial sizes."""
        # Set initial sizes based on design specifications
        # Tab area, Command panel, Progress panel, Log area
        self.splitter.setSizes([300, 120, 100, 200])
        self.splitter.setStretchFactor(0, 0)  # Tab area: not stretchable
        self.splitter.setStretchFactor(1, 0)  # Command panel: fixed
        self.splitter.setStretchFactor(2, 0)  # Progress panel: fixed
        self.splitter.setStretchFactor(3, 1)  # Log area: stretchable
        self.splitter.setChildrenCollapsible(False)  # Prevent collapse

    def _retranslate_ui(self):
        """Retranslate UI elements."""
        # Set window title
        self.setWindowTitle(get_app_title())
        
        # Retranslate pages
        self.basic_page.retranslate_ui()
        self.webpage_page.retranslate_ui()
        self.advanced_page.retranslate_ui()
        self.about_page.retranslate_ui()
        
        # Retranslate components
        self.command_panel.retranslate_ui()
        self.progress_panel.retranslate_ui()
        self.log_panel.retranslate_ui()
        
        # Set tab titles
        self.tabs.setTabText(0, "Basic")
        self.tabs.setTabText(1, "Webpage")
        self.tabs.setTabText(2, "Advanced")
        self.tabs.setTabText(3, "About")

    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect splitter moved signal for responsive behavior
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        
        # Connect page signals
        self._connect_page_signals()
        
        # Connect component signals
        self._connect_component_signals()
        
        # Override showEvent to force correct splitter behavior
        self.showEvent = self._on_show_event

    def _connect_page_signals(self):
        """Connect page signals to main window handlers."""
        # Basic page signals
        self.basic_page.urlListChanged.connect(self._on_url_list_changed)
        self.basic_page.outputDirChanged.connect(self._on_output_dir_changed)
        
        # Webpage page signals
        self.webpage_page.optionsChanged.connect(self._on_options_changed)
        
        # Advanced page signals
        self.advanced_page.openUserDataRequested.connect(self._open_user_data)
        self.advanced_page.restoreDefaultConfigRequested.connect(self._restore_default_config)
        self.advanced_page.languageChanged.connect(self._on_language_changed)
        self.advanced_page.logLevelChanged.connect(self._on_log_level_changed)
        self.advanced_page.debugModeChanged.connect(self._on_debug_mode_changed)
        
        # About page signals
        self.about_page.checkUpdatesRequested.connect(self._check_updates)
        self.about_page.openHomepageRequested.connect(self._open_homepage)

    def _connect_component_signals(self):
        """Connect component signals to main window handlers."""
        # Command panel signals
        self.command_panel.restoreRequested.connect(self._restore_session)
        self.command_panel.importRequested.connect(self._import_session)
        self.command_panel.exportRequested.connect(self._export_session)
        self.command_panel.convertRequested.connect(self._on_convert)
        
        # Progress panel signals
        self.progress_panel.progressUpdated.connect(self._update_progress)
        
        # Log panel signals
        self.log_panel.logCleared.connect(self._clear_log)
        self.log_panel.logCopied.connect(self._copy_log)

    def _on_splitter_moved(self, pos: int, index: int):
        """Handle splitter movement to enforce minimum sizes."""
        sizes = self.splitter.sizes()
        min_sizes = [300, 120, 100, 150]  # Tab, Command, Progress, Log minimum heights
        
        # Check if any area needs adjustment
        if any(sizes[i] < min_sizes[i] for i in range(len(sizes))):
            # Temporarily disconnect to avoid recursion
            self.splitter.splitterMoved.disconnect(self._on_splitter_moved)
            
            # Apply minimum sizes
            adjusted_sizes = [max(sizes[i], min_sizes[i]) for i in range(len(sizes))]
            self.splitter.setSizes(adjusted_sizes)
            
            # Reconnect signal
            self.splitter.splitterMoved.connect(self._on_splitter_moved)

    def _on_show_event(self, event):
        """Handle window show event to force correct splitter behavior."""
        super().showEvent(event)
        
        # Force splitter to behave correctly by setting sizes explicitly
        QTimer.singleShot(50, self._force_splitter_config)

    def _force_splitter_config(self):
        """Force splitter configuration after window is shown."""
        # Get current splitter sizes
        current_sizes = self.splitter.sizes()
        current_tab_height = current_sizes[0]
        
        # Store this as the "remembered" tab height
        self.remembered_tab_height = current_tab_height
        
        # Get current window height
        window_height = self.height()
        
        # Calculate desired sizes
        tab_height = current_tab_height
        command_height = 120
        progress_height = 100
        log_height = window_height - tab_height - command_height - progress_height - 32
        
        # Ensure minimum log height
        if log_height < 150:
            log_height = 150
        
        # Force set the sizes
        self.splitter.setSizes([tab_height, command_height, progress_height, log_height])
        
        # Reconfigure stretch factors
        self.splitter.setStretchFactor(0, 0)  # Tab area fixed
        self.splitter.setStretchFactor(1, 0)  # Command panel fixed
        self.splitter.setStretchFactor(2, 0)  # Progress panel fixed
        self.splitter.setStretchFactor(3, 1)  # Log area stretchable

    def _get_current_state(self) -> dict:
        """Get current application state for session saving."""
        # Get data from pages
        basic_config = self.basic_page.get_config()
        webpage_config = self.webpage_page.get_config()
        
        return {
            "urls": basic_config.get("urls", []),
            "output_dir": to_project_relative_path(basic_config.get("output_dir", ""), self.root_dir),
            "use_proxy": webpage_config.get("use_proxy", False),
            "ignore_ssl": webpage_config.get("ignore_ssl", False),
            "download_images": webpage_config.get("download_images", True),
            "filter_site_chrome": webpage_config.get("filter_site_chrome", True),
            "use_shared_browser": webpage_config.get("use_shared_browser", True),
        }

    def _on_event_thread_safe(self, ev: ProgressEvent):
        """Thread-safe event handler with log integration."""
        if not self.ui_ready:
            return
            
        try:
            message = ev.text or ""
            
            # Handle different event types
            if ev.kind == "progress_init":
                self.progress_panel.setProgress(0, "Starting conversion...")
                if message:
                    self.log_panel.appendLog(f"🚀 {message}")
            elif ev.kind == "status":
                if message:
                    self.log_panel.appendLog(f"ℹ️ {message}")
            elif ev.kind == "detail":
                if message:
                    self.log_panel.appendLog(f"📝 {message}")
            elif ev.kind == "progress_step":
                # Update progress
                if ev.data and "completed" in ev.data:
                    completed = ev.data["completed"]
                    total = ev.data.get("total", 0)
                    self.progress_panel.setMultiTaskProgress(completed, total, message)
                    self.log_panel.appendLog(f"📊 Progress: {completed}/{total} URLs")
                else:
                    current = self.progress_panel.progress.value()
                    self.progress_panel.setProgress(current + 1)
            elif ev.kind == "progress_done":
                self.progress_panel.setProgress(100, "Conversion completed")
                self.log_panel.appendLog(f"🎉 {message or 'Conversion completed'}")
                self.is_running = False
                self.command_panel.setConvertButtonText("Convert to Markdown")
            elif ev.kind == "stopped":
                self.log_panel.appendLog(f"⏹️ {message or 'Conversion stopped'}")
                self.is_running = False
                self.command_panel.setConvertButtonText("Convert to Markdown")
            elif ev.kind == "error":
                self.log_panel.appendLog(f"❌ Error: {message or 'Unknown error'}")
                self.is_running = False
                self.command_panel.setConvertButtonText("Convert to Markdown")
            
        except Exception as e:
            self.log_panel.appendLog(f"❌ Event handler error: {e}")

    # Signal handler methods
    def _on_url_list_changed(self, urls: list):
        """Handle URL list changes."""
        self.log_panel.appendLog(f"URL list updated: {len(urls)} URLs")

    def _on_output_dir_changed(self, path: str):
        """Handle output directory changes."""
        self.log_panel.appendLog(f"Output directory changed: {path}")

    def _on_options_changed(self, options: dict):
        """Handle conversion options changes."""
        self.log_panel.appendLog("Conversion options updated")

    def _open_user_data(self):
        """Open user data directory."""
        import subprocess
        import platform
        data_path = self.advanced_page.get_user_data_path()
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", data_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", data_path])
            else:  # Linux
                subprocess.run(["xdg-open", data_path])
            self.log_panel.appendLog(f"Opened user data directory: {data_path}")
        except Exception as e:
            self.log_panel.appendLog(f"Failed to open directory: {e}")

    def _restore_default_config(self):
        """Restore default configuration."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Restore Default Config",
            "Are you sure you want to restore default configuration? This will reset all settings.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Reset to default values
            self.basic_page.set_config({"urls": [], "output_dir": self.output_dir_var})
            self.webpage_page.set_config({
                "use_proxy": False,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            })
            self.log_panel.appendLog("Default configuration restored")

    def _on_language_changed(self, lang_code: str):
        """Handle language changes."""
        if lang_code != self.translator.language:
            self.translator.load_language(lang_code)
            self._retranslate_ui()
            self.log_panel.appendLog(f"Language changed to: {lang_code}")

    def _on_log_level_changed(self, level: str):
        """Handle log level changes."""
        self.log_panel.appendLog(f"Log level changed to: {level}")

    def _on_debug_mode_changed(self, enabled: bool):
        """Handle debug mode changes."""
        self.log_panel.appendLog(f"Debug mode {'enabled' if enabled else 'disabled'}")

    def _check_updates(self):
        """Check for updates."""
        self.log_panel.appendLog("Checking for updates...")

    def _open_homepage(self):
        """Open project homepage."""
        import webbrowser
        webbrowser.open("https://github.com/VimWei/MarkdownAll")
        self.log_panel.appendLog("Opened project homepage")

    def _restore_session(self):
        """Restore last session."""
        try:
            sessions_dir = os.path.join(self.root_dir, "data", "sessions")
            state = load_json_from_root(sessions_dir, "last_state.json")
            if not state:
                self.log_panel.appendLog("No session found to restore")
                return
            self._apply_state(state)
            self.log_panel.appendLog("Session restored successfully")
        except Exception as e:
            self.log_panel.appendLog(f"Failed to restore session: {e}")

    def _import_session(self):
        """Import session from file."""
        from PySide6.QtWidgets import QFileDialog
        sessions_dir = os.path.join(self.root_dir, "data", "sessions")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Session", sessions_dir, "JSON Files (*.json)"
        )
        if filename:
            try:
                config = load_config(filename)
                self._apply_state(config)
                self.log_panel.appendLog(f"Session imported from: {os.path.basename(filename)}")
            except Exception as e:
                self.log_panel.appendLog(f"Failed to import session: {e}")

    def _export_session(self):
        """Export session to file."""
        from PySide6.QtWidgets import QFileDialog
        sessions_dir = os.path.join(self.root_dir, "data", "sessions")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Session", sessions_dir, "JSON Files (*.json)"
        )
        if filename:
            try:
                data = self._get_current_state()
                save_config(filename, data)
                self.log_panel.appendLog(f"Session exported to: {os.path.basename(filename)}")
            except Exception as e:
                self.log_panel.appendLog(f"Failed to export session: {e}")

    def _on_convert(self):
        """Handle convert button click."""
        if self.is_running:
            self._stop_conversion()
            return
        
        # Get URLs and options
        urls = self.basic_page.get_urls()
        if not urls:
            url = self.basic_page.url_entry.text().strip()
            if not url:
                self.log_panel.appendLog("No URLs to convert")
                return
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            urls = [url]
        
        out_dir = self.basic_page.get_output_dir().strip() or os.getcwd()
        options_dict = self.webpage_page.get_options()
        
        # Start conversion
        self.is_running = True
        self.command_panel.setConvertButtonText("Stop")
        self.progress_panel.setProgress(0, "Starting conversion...")
        self.log_panel.appendLog(f"Starting conversion of {len(urls)} URLs")
        
        # Create conversion objects
        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(**options_dict)
        
        # Start conversion through ViewModel
        self.vm.start(reqs, out_dir, options, self._on_event_thread_safe, self.signals)

    def _stop_conversion(self):
        """Stop conversion process."""
        self.vm.stop(self._on_event_thread_safe)
        self.log_panel.appendLog("Conversion stop requested")

    def _update_progress(self, value: int, text: str):
        """Update progress display."""
        self.progress_panel.setProgress(value, text)

    def _clear_log(self):
        """Clear log content."""
        self.log_panel.clearLog()

    def _copy_log(self):
        """Copy log content to clipboard."""
        self.log_panel._copy_log()

    def _apply_state(self, state: dict):
        """Apply session state to UI."""
        # Apply to basic page
        basic_config = {
            "urls": state.get("urls", []),
            "output_dir": resolve_project_path(state.get("output_dir", ""), self.root_dir)
        }
        self.basic_page.set_config(basic_config)
        
        # Apply to webpage page
        webpage_config = {
            "use_proxy": state.get("use_proxy", False),
            "ignore_ssl": state.get("ignore_ssl", False),
            "download_images": state.get("download_images", True),
            "filter_site_chrome": state.get("filter_site_chrome", True),
            "use_shared_browser": state.get("use_shared_browser", True),
        }
        self.webpage_page.set_config(webpage_config)


# Alias for backward compatibility
PySideApp = MainWindow
