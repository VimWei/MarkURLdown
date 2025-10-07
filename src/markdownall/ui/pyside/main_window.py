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
from .components import CommandPanel, LogPanel

# Import managers for enhanced functionality
from markdownall.services.config_service import ConfigService
from markdownall.services.startup_service import StartupService
from markdownall.utils.memory_optimizer import MemoryOptimizer
from .startup_manager import StartupManager, BackgroundInitializer
from .error_handler import ErrorHandler, ErrorRecovery


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
        
        # Initialize internal flags early to avoid AttributeError during signal connections
        self._suppress_change_logs = False
        self._images_dl_logged = False
        self._images_dl_logged_tasks: set[str] = set()
        
        # Initialize enhanced managers
        self.config_service = ConfigService(root_dir)
        self.startup_service = StartupService(root_dir)
        self.startup_manager = StartupManager(self.startup_service)
        self.error_handler = ErrorHandler(self.config_service)
        self.memory_optimizer = MemoryOptimizer()
        
        # Connect manager signals
        self.startup_manager.startup_complete.connect(self._on_startup_complete)
        self.startup_manager.startup_error.connect(self._on_startup_error)
        self.error_handler.error_occurred.connect(self._on_error_occurred)
        self.error_handler.performance_warning.connect(self._on_performance_warning)
        
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
        
        # Apply modern styling (模仿MdxScraper)
        self._apply_modern_styling()
        
        # Load saved configuration
        self._load_config()
        
        # Override showEvent to force splitter behavior after window is shown (模仿MdxScraper)
        self.showEvent = self._on_show_event
        
        # Connect progress signals for thread-safe UI updates
        self.signals.progress_event.connect(self._on_event_thread_safe)
        self.ui_ready = True

    def closeEvent(self, event):
        """Handle window close event with session state saving."""
        try:
            # Save current configuration using ConfigService
            self._save_config()
        except Exception as e:
            print(f"Error saving configuration on exit: {e}")
        finally:
            event.accept()

    def _setup_ui(self):
        """Setup the main UI layout with tabbed interface and splitter."""
        # Set window properties
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 基于布局计算设置窗口大小
        # 布局计算: Tab(270) + Command(120) + Log(160) + 边距(50) = 600px
        self.resize(800, 600)  # 初始大小: 800x600 (基于精确布局计算)
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        # 最小尺寸将在_configure_splitter中统一设置
        
        # Create central widget with vertical layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main vertical layout (模仿MdxScraper)
        from PySide6.QtWidgets import QVBoxLayout
        main_layout = QVBoxLayout(central_widget)
        # Tighter global margins and spacing for a compact layout
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Create splitter for all areas (tabs, command, log) - like MdxScraper
        self.splitter = QSplitter(Qt.Vertical, self)
        
        # Setup tabbed interface
        self._setup_tabbed_interface()
        
        # Setup components
        self._setup_components()
        
        # Add all widgets to splitter (like MdxScraper)
        self.splitter.addWidget(self.tabs)           # Tab area (index 0)
        self.splitter.addWidget(self.command_panel)  # Command panel (index 1)
        self.splitter.addWidget(self.log_panel)      # Log area (index 2)
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Configure splitter
        self._configure_splitter()

    def _setup_tabbed_interface(self):
        """Setup the tabbed interface with pages."""
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(300)  # 进一步增加最小高度，确保内容不堆叠
        
        # Create real pages
        self._create_pages()

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
        """Setup components (CommandPanel + LogPanel)."""
        # Create CommandPanel - Session management, conversion control + progress bar
        self.command_panel = CommandPanel(self, self.translator)
        
        # Create LogPanel - Log area (like MdxScraper)
        self.log_panel = LogPanel(self, self.translator)

    def _configure_splitter(self):
        """Configure splitter behavior and initial sizes (适配MarkdownAll需求)."""
        # Configure splitter for all three areas: tabs, command panel, log panel
        # 基于布局计算设置初始尺寸
        self.splitter.setSizes([270, 120, 160])  # Tab(270) + Command(120) + Log(160) = 550px
        self.splitter.setStretchFactor(0, 0)  # Tab area fixed height (not stretchable)
        self.splitter.setStretchFactor(1, 0)  # Command panel fixed
        self.splitter.setStretchFactor(2, 1)  # Log area stretchable
        self.splitter.setChildrenCollapsible(False)  # Prevent collapse
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        
        # 设置整体窗口最小尺寸，基于精确布局计算
        # 布局计算: Tab(270) + Command(120) + Log(160) + 边距(50) = 600px
        self.setMinimumSize(800, 600)  # 最小尺寸: 800x650 (基于精确布局计算)
        
        # Override showEvent to force splitter behavior after window is shown
        self.showEvent = self._on_show_event

    def _on_show_event(self, event):
        """Handle window show event to force correct splitter behavior (模仿MdxScraper)."""
        super().showEvent(event)
        
        # Force splitter to behave correctly by setting sizes explicitly
        # This ensures tab area stays fixed and only log area stretches
        QTimer.singleShot(50, self._force_splitter_config)

    def _force_splitter_config(self):
        """Force splitter configuration after window is shown (模仿MdxScraper)."""
        # Get current splitter sizes to capture the actual tab height
        current_sizes = self.splitter.sizes()
        current_tab_height = current_sizes[0]  # Capture current tab height
        
        # Store this as the "remembered" tab height
        self.remembered_tab_height = current_tab_height
        
        # Get current window height
        window_height = self.height()
        
        # Calculate desired sizes: use current tab height, command fixed, log gets the rest
        tab_height = current_tab_height  # Use current tab height as the "remembered" height
        command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
        log_height = window_height - tab_height - command_height - 32  # 32 for margins
        
        # Ensure minimum log height
        if log_height < 150:
            log_height = 150
        
        # Force set the sizes - this "teaches" the splitter to remember the current tab height
        self.splitter.setSizes([tab_height, command_height, log_height])
        
        # Reconfigure stretch factors to ensure they stick
        self.splitter.setStretchFactor(0, 0)  # Tab area fixed
        self.splitter.setStretchFactor(1, 0)  # Command panel fixed
        self.splitter.setStretchFactor(2, 1)  # Log area stretchable
        
        # Force the splitter to "remember" these sizes by triggering a resize
        # This ensures the splitter's internal memory is set correctly
        QTimer.singleShot(10, self._reinforce_splitter_memory)

    def _reinforce_splitter_memory(self):
        """Reinforce the splitter's memory of correct sizes (模仿MdxScraper)."""
        # Get current sizes
        current_sizes = self.splitter.sizes()
        
        # If tab area is not at the remembered height, force it back
        if (hasattr(self, "remembered_tab_height") and 
            current_sizes[0] != self.remembered_tab_height):
            
            # Recalculate with remembered tab height
            window_height = self.height()
            tab_height = self.remembered_tab_height
            command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
            log_height = window_height - tab_height - command_height - 32
            
            if log_height < 150:
                log_height = 150
            
            # Force set the sizes again to reinforce the memory
            self.splitter.setSizes([tab_height, command_height, log_height])
            
            # Reapply stretch factors
            self.splitter.setStretchFactor(0, 0)  # Tab area fixed
            self.splitter.setStretchFactor(1, 0)  # Command panel fixed
            self.splitter.setStretchFactor(2, 1)  # Log area stretchable

    def _on_splitter_moved(self, pos, index):
        """Handle splitter movement (模仿MdxScraper)."""
        # MdxScraper 中这个方法主要是空的，主要依靠 showEvent 和记忆强化机制
        pass

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
        self.log_panel.retranslate_ui()
        
        # Set tab titles
        t = self.translator.t
        self.tabs.setTabText(0, t("tab_basic"))
        self.tabs.setTabText(1, t("tab_webpage"))
        self.tabs.setTabText(2, t("tab_advanced"))
        self.tabs.setTabText(3, t("tab_about"))

    def _connect_signals(self):
        """Connect signals and slots."""
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
        self.command_panel.stopRequested.connect(self._stop_conversion)
        
        # Progress panel signals (now in command_panel)
        # self.command_panel already has progress bar, no separate signals needed
        
        # Log panel signals
        self.log_panel.logCopied.connect(self._copy_log)

    def _on_show_event(self, event):
        """Handle window show event to force correct splitter behavior (模仿MdxScraper)."""
        super().showEvent(event)
        
        # Force splitter to behave correctly by setting sizes explicitly
        # This ensures tab area stays fixed and only log area stretches
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._force_splitter_config)

    def _force_splitter_config(self):
        """Force splitter configuration after window is shown (模仿MdxScraper)."""
        # Get current splitter sizes to capture the actual tab height
        current_sizes = self.splitter.sizes()
        current_tab_height = current_sizes[0]  # Capture current tab height
        
        # Store this as the "remembered" tab height
        self.remembered_tab_height = current_tab_height
        
        # Get current window height
        window_height = self.height()
        
        # Calculate desired sizes: use current tab height, command fixed, log gets the rest
        tab_height = current_tab_height  # Use current tab height as the "remembered" height
        command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
        log_height = window_height - tab_height - command_height - 32  # 32 for margins
        
        # Ensure minimum log height
        if log_height < 150:
            log_height = 150
        
        # Force set the sizes - this "teaches" the splitter to remember the current tab height
        self.splitter.setSizes([tab_height, command_height, log_height])
        
        # Reconfigure stretch factors to ensure they stick
        self.splitter.setStretchFactor(0, 0)  # Tab area fixed
        self.splitter.setStretchFactor(1, 0)  # Command panel fixed
        self.splitter.setStretchFactor(2, 1)  # Log area stretchable
        
        # Force the splitter to "remember" these sizes by triggering a resize
        # This ensures the splitter's internal memory is set correctly
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._reinforce_splitter_memory)

    def _reinforce_splitter_memory(self):
        """Reinforce the splitter's memory of correct sizes (模仿MdxScraper)."""
        # Get current sizes
        current_sizes = self.splitter.sizes()
        
        # If tab area is not at the remembered height, force it back
        if (hasattr(self, "remembered_tab_height") 
            and current_sizes[0] != self.remembered_tab_height):
            
            # Recalculate with remembered tab height
            window_height = self.height()
            tab_height = self.remembered_tab_height
            command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
            log_height = window_height - tab_height - command_height - 32
            
            if log_height < 150:
                log_height = 150
            
            # Force set the sizes again to reinforce the memory
            self.splitter.setSizes([tab_height, command_height, log_height])
            
            # Reapply stretch factors
            self.splitter.setStretchFactor(0, 0)  # Tab area fixed
            self.splitter.setStretchFactor(1, 0)  # Command panel fixed
            self.splitter.setStretchFactor(2, 1)  # Log area stretchable

    def _apply_modern_styling(self):
        """Apply modern styling to the application (模仿MdxScraper)."""
        try:
            from .styles.theme_loader import ThemeLoader
            theme_loader = ThemeLoader("default")
            theme_loader.apply_theme_to_widget(self)
        except Exception as e:
            print(f"Warning: Could not apply theme: {e}")

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
        """Enhanced event handler - converts ProgressEvent to direct log calls (MdxScraper style)."""
        if not self.ui_ready:
            return
            
        try:
            message = ev.text or ""
            
            # Handle all event types with direct log calls (learning from MdxScraper)
            if ev.kind == "progress_init":
                self.command_panel.set_progress(0, "Starting conversion...")
                # Reset per-run image download log trackers
                self._images_dl_logged = False
                self._images_dl_logged_tasks.clear()
                if message:
                    self.log_info(f"Starting conversion: {message}")
                    
            elif ev.kind == "status":
                # Prefer structured status data for task grouping when available
                if isinstance(ev.data, dict) and "url" in ev.data:
                    url = ev.data["url"]
                    idx = ev.data.get("idx", 0)
                    total = ev.data.get("total", 0)
                    if total and total > 1:
                        task_id = f"Task {idx}/{total}"
                        self.log_panel.appendTaskLog(task_id, f"Processing: {url}", "🔄")
                    else:
                        self.log_info(f"Processing URL: {url}")
                elif message:
                    # Fallback to plain message
                    self.log_info(message)
                        
            elif ev.kind == "detail":
                # Detail messages - handle specific keys with task grouping
                if ev.key == "convert_detail_done" and ev.data:
                    title = (ev.data.get("title") if isinstance(ev.data, dict) else "") or "无标题"
                    # Check if this is part of a multi-task operation
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 1
                    if total > 1:
                        _idx_val = ev.data.get("idx") if isinstance(ev.data, dict) else None
                        idx = int(_idx_val) if isinstance(_idx_val, int) else 0
                        task_id = f"Task {idx}/{total}"
                        self.log_panel.appendTaskLog(task_id, f"URL处理成功: {title}", "✅")
                    else:
                        self.log_success(f"✅ URL处理成功: {title}")
                elif ev.key == "images_dl_progress" and ev.data:
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    # Condense progress logs: only log once per task (or once per run)
                    _task_total_val = ev.data.get("task_total") if isinstance(ev.data, dict) else None
                    task_total = int(_task_total_val) if isinstance(_task_total_val, int) else 1
                    if task_total > 1:
                        _task_idx_val = ev.data.get("task_idx") if isinstance(ev.data, dict) else None
                        task_idx = int(_task_idx_val) if isinstance(_task_idx_val, int) else 0
                        task_id = f"Task {task_idx}/{task_total}"
                        if task_id not in self._images_dl_logged_tasks:
                            self._images_dl_logged_tasks.add(task_id)
                            self.log_panel.appendTaskLog(task_id, f"Downloading images: {total} images")
                    else:
                        if not self._images_dl_logged:
                            self._images_dl_logged = True
                            self.log_info(f"Downloading images: {total} images")
                elif ev.key == "images_dl_done" and ev.data:
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    # Use task-specific logging if part of multi-task
                    _task_total_val = ev.data.get("task_total") if isinstance(ev.data, dict) else None
                    task_total = int(_task_total_val) if isinstance(_task_total_val, int) else 1
                    if task_total > 1:
                        _task_idx_val = ev.data.get("task_idx") if isinstance(ev.data, dict) else None
                        task_idx = int(_task_idx_val) if isinstance(_task_idx_val, int) else 0
                        task_id = f"Task {task_idx}/{task_total}"
                        # Ensure the initial download line exists for this task
                        if task_id not in self._images_dl_logged_tasks:
                            self._images_dl_logged_tasks.add(task_id)
                            self.log_panel.appendTaskLog(task_id, f"Downloading images: {total} images")
                        self.log_panel.appendTaskLog(task_id, f"Images downloaded: {total} images")
                    else:
                        # Ensure the initial download line exists for single-task runs
                        if not self._images_dl_logged:
                            self._images_dl_logged = True
                            self.log_info(f"Downloading images: {total} images")
                        self.log_success(f"Images downloaded: {total} images")
                elif ev.key == "convert_shared_browser_started":
                    self.log_info("Shared browser started")
                elif message:
                    # Default detail message
                    self.log_info(message)
                    
            elif ev.kind == "progress_step":
                # Update progress bar
                if isinstance(ev.data, dict) and "completed" in ev.data:
                    _completed_val = ev.data.get("completed")
                    _total_val = ev.data.get("total")
                    completed = int(_completed_val) if isinstance(_completed_val, int) else 0
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    progress_value = int((completed / total) * 100) if total and total > 0 else 0
                    self.command_panel.set_progress(progress_value, f"{completed}/{total} URLs")
                else:
                    current = self.command_panel.progress.value()
                    self.command_panel.set_progress(current + 1)
                    
            elif ev.kind == "progress_done":
                self.command_panel.set_progress(100, "Conversion completed")
                # Use multi-task summary if available
                if ev.data and "completed" in ev.data and "total" in ev.data:
                    completed = ev.data["completed"]
                    total = ev.data["total"]
                    if total > 1:
                        # Calculate successful and failed counts
                        successful = ev.data.get("successful", completed)
                        failed = ev.data.get("failed", total - completed)
                        self.log_panel.appendMultiTaskSummary(successful, failed, total)
                    else:
                        self.log_success(message or "Conversion completed")
                else:
                    self.log_success(message or "Conversion completed")
                self.is_running = False
                self.command_panel.setConvertingState(False)
                
            elif ev.kind == "stopped":
                self.log_warning(message or "Conversion stopped")
                self.is_running = False
                self.command_panel.setConvertingState(False)
                
            elif ev.kind == "error":
                self.log_error(message or "Unknown error")
                self.is_running = False
                self.command_panel.setConvertingState(False)
            
        except Exception as e:
            self.log_error(f"Event handler error: {e}")

    # Signal handler methods
    def _on_url_list_changed(self, urls: list):
        """Handle URL list changes."""
        if self._suppress_change_logs:
            return
        self.log_panel.appendLog(f"URL list updated: {len(urls)} URLs")

    def _on_output_dir_changed(self, path: str):
        """Handle output directory changes."""
        if self._suppress_change_logs:
            return
        self.log_panel.appendLog(f"Output directory changed: {path}")

    def _on_options_changed(self, options: dict):
        """Handle conversion options changes."""
        if self._suppress_change_logs:
            return
        self.log_panel.appendLog("Conversion options updated")

    def _open_user_data(self):
        """Open user data directory."""
        import subprocess
        import platform
        import os as _os
        data_path = self.advanced_page.get_user_data_path()
        try:
            # Resolve relative paths against project root and ensure directory exists
            if not data_path:
                # Default to project_root/data when field is empty
                data_path = _os.path.join(self.root_dir, "data")
            if not _os.path.isabs(data_path):
                data_path = _os.path.join(self.root_dir, data_path)
            data_path = _os.path.abspath(data_path)
            if not _os.path.exists(data_path):
                _os.makedirs(data_path, exist_ok=True)

            if platform.system() == "Windows":
                subprocess.run(["explorer", data_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", data_path])
            else:  # Linux
                subprocess.run(["xdg-open", data_path])
            self.log_panel.appendLog(f"Opened user data directory: {data_path}")
            # Update Advanced page display to show the resolved absolute path
            try:
                self.advanced_page.set_user_data_path(data_path)
            except Exception:
                pass
        except Exception as e:
            self.log_panel.appendLog(f"Failed to open directory: {e}")

    def _restore_default_config(self):
        """Restore default configuration."""
        try:
            # Use config service to reset to defaults
            self.config_service.reset_to_defaults()
            
            # Sync UI from the reset configuration
            self._sync_ui_from_config()
            
            # Save the restored config
            self._save_config()
            
            self.log_success("Default configuration restored successfully")
        except Exception as e:
            self.log_error(f"Failed to restore default config: {e}")

    def _sync_ui_from_config(self):
        """Sync UI display from configuration."""
        try:
            config = self.config_service.get_all_config()
            
            # Update basic page
            basic_config = config["basic"]
            basic_config["output_dir"] = self.output_dir_var  # Preserve existing default
            self.basic_page.set_config(basic_config)
            
            # Update webpage page
            self.webpage_page.set_config(config["webpage"])
            
            # Update advanced page
            self.advanced_page.set_config(config["advanced"])
            
        except Exception as e:
            self.log_error(f"Failed to sync UI from config: {e}")

    def _on_language_changed(self, lang_code: str):
        """Handle language changes."""
        try:
            # Handle auto language detection
            if lang_code == "auto":
                import locale
                system_lang = locale.getdefaultlocale()[0]
                if system_lang and system_lang.startswith('zh'):
                    lang_code = "zh"
                else:
                    lang_code = "en"
            
            # Update translator
            if lang_code != self.translator.language:
                self.translator.load_language(lang_code)
                self._retranslate_ui()
                
                # Save language setting
                self._save_config()
                
                self.log_info(f"Language changed to: {lang_code}")
        except Exception as e:
            self.log_error(f"Failed to change language: {e}")

    # Debug mode removed

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
                # Suppress noisy change logs during bulk apply
                self._suppress_change_logs = True
                self._apply_state(config)
                # Stop any pending debounced optionsChanged emission
                try:
                    if hasattr(self.webpage_page, "_options_changed_timer"):
                        self.webpage_page._options_changed_timer.stop()
                except Exception:
                    pass
                self._suppress_change_logs = False
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
        self.command_panel.setConvertingState(True)  # Show stop button, hide convert button
        self.command_panel.set_progress(0, "Starting conversion...")
        
        # Create conversion objects
        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(**options_dict)
        
        # Start conversion through ViewModel
        # 传入 UI 作为日志接收端（LoggerAdapter 将调用本窗口的 log_* 方法与 LogPanel 扩展方法）
        self.vm.start(reqs, out_dir, options, self._on_event_thread_safe, self.signals, self)

    def _stop_conversion(self):
        """Stop conversion process."""
        self.vm.stop(self._on_event_thread_safe)
        self.log_panel.appendLog("Conversion stop requested")

    def _update_progress(self, value: int, text: str):
        """Update progress display."""
        self.command_panel.set_progress(value, text)


    def _copy_log(self):
        """Copy log content to clipboard."""
        try:
            # 直接访问剪贴板，避免通过 log_panel 信号链导致递归
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.log_panel.getLogContent())
            self.log_panel.appendLog("Log copied to clipboard")
        except Exception as e:
            self.log_panel.appendLog(f"Copy to clipboard failed: {e}")

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
    
    def _on_startup_complete(self):
        """Handle startup completion."""
        print("Startup sequence completed successfully")
        # Any post-startup initialization can go here
        
    def _on_startup_error(self, error_message: str):
        """Handle startup error."""
        print(f"Startup error: {error_message}")
        # Show error to user or attempt recovery
        
    def _on_error_occurred(self, error_type: str, error_message: str):
        """Handle error occurrence."""
        self.log_error(f"Error occurred: {error_type} - {error_message}")
        # Update UI to show error status

    def _on_performance_warning(self, warning_message: str):
        """Handle performance warning."""
        self.log_warning(f"Performance warning: {warning_message}")

    # Direct log methods (adopting MdxScraper's simple design)
    def log_info(self, message: str) -> None:
        """Log info message directly."""
        self.log_panel.appendLog(message)

    def log_success(self, message: str) -> None:
        """Log success message directly."""
        self.log_panel.appendLog(message)

    def log_warning(self, message: str) -> None:
        """Log warning message directly."""
        self.log_panel.appendLog(message)

    def log_error(self, message: str) -> None:
        """Log error message directly."""
        self.log_panel.appendLog(message)

    # log_debug removed
        
    def _on_performance_warning(self, warning_message: str):
        """Handle performance warning."""
        self.log_warning(f"Performance warning: {warning_message}")
        # Show warning to user or take corrective action

    def _save_config(self):
        """Save current configuration using ConfigService."""
        try:
            # Get current state from all pages
            state = self._get_current_state()
            
            # Update config service with current state
            self.config_service.set_basic_config({
                "urls": state.get("urls", []),
                "output_dir": state.get("output_dir", "")
            })
            
            self.config_service.set_webpage_config({
                "use_proxy": state.get("use_proxy", False),
                "ignore_ssl": state.get("ignore_ssl", False),
                "download_images": state.get("download_images", True),
                "filter_site_chrome": state.get("filter_site_chrome", True),
                "use_shared_browser": state.get("use_shared_browser", True)
            })
            
            # Add advanced page settings
            advanced_config = self.advanced_page.get_config()
            self.config_service.set_advanced_config({
                "language": advanced_config.get("language", "auto"),
            })
            
            # Save session and settings
            self.config_service.save_session()
            self.config_service.save_settings()
            
        except Exception as e:
            self.log_error(f"Failed to save config: {e}")

    def _load_config(self):
        """Load configuration using ConfigService."""
        try:
            # Only load application settings on startup (no session restore)
            settings_loaded = self.config_service.load_settings()
            
            # Always sync UI from defaults + settings
            self._sync_ui_from_config()
            
            if not settings_loaded:
                # No settings found, using defaults
                self.log_info("No saved settings found, using defaults")
                
        except Exception as e:
            self.log_error(f"Failed to load config: {e}")

    def _sync_ui_from_config(self):
        """Sync UI display from configuration."""
        try:
            config = self.config_service.get_all_config()
            
            # Update basic page
            basic_config = config["basic"]
            # Respect existing value; if missing/empty, fall back to default project output dir
            if not basic_config.get("output_dir"):
                basic_config["output_dir"] = self.output_dir_var
            
            # Suppress noisy change logs while applying config to UI widgets
            self._suppress_change_logs = True
            self.basic_page.set_config(basic_config)
            
            # Update webpage page
            self.webpage_page.set_config(config["webpage"])
            
            # Update advanced page
            self.advanced_page.set_config(config["advanced"])
        
        except Exception as e:
            self.log_error(f"Failed to sync UI from config: {e}")
        finally:
            # Re-enable change logs
            self._suppress_change_logs = False


# Alias for backward compatibility
PySideApp = MainWindow
