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
    resolve_project_path,
    to_project_relative_path,
)

# Import managers for enhanced functionality
from markdownall.services.config_service import ConfigService
from markdownall.services.startup_service import StartupService
from markdownall.ui.pyside.splash import show_immediate_splash
from markdownall.ui.viewmodel import ViewModel
from markdownall.utils.memory_optimizer import MemoryOptimizer
from markdownall.version import get_app_title

from .components import CommandPanel, LogPanel
from .error_handler import ErrorHandler, ErrorRecovery

# Import pages and components
from .pages import AboutPage, AdvancedPage, BasicPage, WebpagePage


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
        # Progress interpolation state
        self._progress_total_urls: int = 0
        self._progress_completed_urls: int = 0
        self._current_task_idx: int = 0
        # Define intra-task phases (equal weight). Images handled specially.
        self._phase_order: list[str] = [
            "phase_fetch_start",
            "phase_parse_start",
            "phase_clean_start",
            "phase_convert_start",
            "phase_images",  # virtual phase key for images progress
            "phase_write_start",
        ]
        self._current_phase_key: str | None = None
        self._current_images_progress: tuple[int, int] | None = None  # (idx, total)

        # Initialize enhanced managers
        self.config_service = ConfigService(root_dir)
        self.startup_service = StartupService(root_dir)
        self.error_handler = ErrorHandler(self.config_service)
        self.memory_optimizer = MemoryOptimizer()

        # Connect manager signals
        self.error_handler.error_occurred.connect(self._on_error_occurred)
        self.error_handler.performance_warning.connect(self._on_performance_warning)

        # Default configuration (preserve existing defaults)
        self.output_dir_var = os.path.abspath(os.path.join(root_dir, "data", "output"))
        self.use_proxy_var = False
        self.ignore_ssl_var = False
        self.download_images_var = True
        self.filter_site_chrome_var = True
        self.use_shared_browser_var = True
        self.handler_override_var = None

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
        self.resize(1024, 650)  # 初始大小
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
        self.splitter.addWidget(self.tabs)  # Tab area (index 0)
        self.splitter.addWidget(self.command_panel)  # Command panel (index 1)
        self.splitter.addWidget(self.log_panel)  # Log area (index 2)

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
        if (
            hasattr(self, "remembered_tab_height")
            and current_sizes[0] != self.remembered_tab_height
        ):

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
        self.command_panel.restoreRequested.connect(self._restore_config)
        self.command_panel.importRequested.connect(self._import_config)
        self.command_panel.exportRequested.connect(self._export_config)
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
        if (
            hasattr(self, "remembered_tab_height")
            and current_sizes[0] != self.remembered_tab_height
        ):

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
            "output_dir": to_project_relative_path(
                basic_config.get("output_dir", ""), self.root_dir
            ),
            "use_proxy": webpage_config.get("use_proxy", False),
            "ignore_ssl": webpage_config.get("ignore_ssl", False),
            "download_images": webpage_config.get("download_images", True),
            "filter_site_chrome": webpage_config.get("filter_site_chrome", True),
            "use_shared_browser": webpage_config.get("use_shared_browser", True),
            "handler_override": webpage_config.get("handler_override"),
        }

    def _on_event_thread_safe(self, ev: ProgressEvent):
        """Enhanced event handler - converts ProgressEvent to direct log calls (MdxScraper style)."""
        if not self.ui_ready:
            return

        try:
            message = ev.text or ""

            # Handle all event types with direct log calls (learning from MdxScraper)
            if ev.kind == "progress_init":
                self.command_panel.set_progress(
                    0,
                    self.translator.t(
                        "convert_init",
                        total=ev.data.get("total", 0) if isinstance(ev.data, dict) else 0,
                    ),
                )
                # Reset per-run image download log trackers
                self._images_dl_logged = False
                self._images_dl_logged_tasks.clear()
                # Reset progress interpolation state
                try:
                    self._progress_total_urls = (
                        int(ev.data.get("total", 0)) if isinstance(ev.data, dict) else 0
                    )
                except Exception:
                    self._progress_total_urls = 0
                self._progress_completed_urls = 0
                self._current_task_idx = 0
                self._current_phase_key = None
                self._current_images_progress = None
                if message:
                    self.log_info(f"Starting conversion: {message}")

            elif ev.kind == "status":
                # Prefer structured status data for task grouping when available
                # Handle localized batch start early to avoid logging raw text
                if ev.key == "batch_start" and ev.data:
                    try:
                        _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                        total = int(_total_val) if isinstance(_total_val, int) else 0
                        self.log_info(self.translator.t("batch_start", total=total))
                    except Exception:
                        pass
                    # Do not fall through to generic message logging for this event
                    return
                if isinstance(ev.data, dict) and "url" in ev.data:
                    url = ev.data["url"]
                    idx = ev.data.get("idx", 0)
                    total = ev.data.get("total", 0)
                    # Track current task index for interpolation
                    try:
                        self._current_task_idx = int(idx) if isinstance(idx, int) else 0
                    except Exception:
                        self._current_task_idx = 0
                    if total and total > 1:
                        task_id = f"Task {idx}/{total}"
                        # Use a plain message without duplicate [idx/total] since task_id already has it
                        self.log_panel.appendTaskLog(
                            task_id, self.translator.t("convert_status_message", url=url), "🔄"
                        )
                    else:
                        self.log_info(
                            self.translator.t("convert_status_running", idx=1, total=1, url=url)
                        )
                elif message:
                    # Fallback to plain message
                    self.log_info(message)
                # Handle phase-bound status keys for interpolation and friendly text
                if ev.key in (
                    "phase_fetch_start",
                    "phase_parse_start",
                    "phase_clean_start",
                    "phase_convert_start",
                    "phase_write_start",
                ):
                    self._current_phase_key = ev.key
                    self._current_images_progress = None
                    self._update_interpolated_progress()
                    # Update friendly status text with current completed/total and percent
                    total = max(self._progress_total_urls, 1)
                    completed = max(0, self._progress_completed_urls)
                    percent = self.command_panel.progress.value()
                    phase_map = {
                        "phase_fetch_start": self.translator.t("progress_phase_fetch"),
                        "phase_parse_start": self.translator.t("progress_phase_parse"),
                        "phase_clean_start": self.translator.t("progress_phase_clean"),
                        "phase_convert_start": self.translator.t("progress_phase_convert"),
                        "phase_write_start": self.translator.t("progress_phase_write"),
                    }
                    phase_text = phase_map.get(ev.key, self.translator.t("progress_processing"))
                    self.command_panel.setProgressText(
                        self.translator.t(
                            "progress_text_with_counts",
                            phase=phase_text,
                            completed=completed,
                            total=total,
                            percent=percent,
                        )
                    )

            elif ev.kind == "detail" or ev.kind == "status":
                # Detail messages - handle specific keys with task grouping
                if ev.key == "conversion_timing" and ev.data:
                    duration = ev.data.get("duration") if isinstance(ev.data, dict) else ""
                    self.log_info(self.translator.t("conversion_timing", duration=duration))
                elif ev.key == "batch_start" and ev.data:
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    self.log_info(self.translator.t("batch_start", total=total))
                elif ev.key == "convert_detail_done" and ev.data:
                    title = (ev.data.get("title") if isinstance(ev.data, dict) else "") or "无标题"
                    # Check if this is part of a multi-task operation
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 1
                    if total > 1:
                        _idx_val = ev.data.get("idx") if isinstance(ev.data, dict) else None
                        idx = int(_idx_val) if isinstance(_idx_val, int) else 0
                        task_id = f"Task {idx}/{total}"
                        self.log_panel.appendTaskLog(
                            task_id, self.translator.t("url_success_message", title=title), "✅"
                        )
                    else:
                        self.log_success(
                            f"✅ {self.translator.t('url_success_message', title=title)}"
                        )
                elif ev.key == "images_dl_progress" and ev.data:
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    # Condense progress logs: only log once per task (or once per run)
                    _task_total_val = (
                        ev.data.get("task_total") if isinstance(ev.data, dict) else None
                    )
                    task_total = int(_task_total_val) if isinstance(_task_total_val, int) else 1
                    # Track images progress for interpolation if available
                    if task_total > 1:
                        _task_idx_val = (
                            ev.data.get("task_idx") if isinstance(ev.data, dict) else None
                        )
                        task_idx = int(_task_idx_val) if isinstance(_task_idx_val, int) else 0
                        self._current_phase_key = "phase_images"
                        self._current_images_progress = (max(0, task_idx), max(1, task_total))
                        self._update_interpolated_progress()
                        # Friendly progress text during images
                        total_urls = max(self._progress_total_urls, 1)
                        completed_urls = max(0, self._progress_completed_urls)
                        percent = self.command_panel.progress.value()
                        self.command_panel.setProgressText(
                            self.translator.t(
                                "images_progress_text",
                                task_idx=task_idx,
                                task_total=task_total,
                                completed=completed_urls,
                                total=total_urls,
                                percent=percent,
                            )
                        )
                    if task_total > 1:
                        _task_idx_val = (
                            ev.data.get("task_idx") if isinstance(ev.data, dict) else None
                        )
                        task_idx = int(_task_idx_val) if isinstance(_task_idx_val, int) else 0
                        task_id = f"Task {task_idx}/{task_total}"
                        if task_id not in self._images_dl_logged_tasks:
                            self._images_dl_logged_tasks.add(task_id)
                            self.log_panel.appendTaskLog(
                                task_id, f"Downloading images: {total} images"
                            )
                    else:
                        if not self._images_dl_logged:
                            self._images_dl_logged = True
                            self.log_info(f"Downloading images: {total} images")
                elif ev.key == "images_dl_done" and ev.data:
                    _total_val = ev.data.get("total") if isinstance(ev.data, dict) else None
                    total = int(_total_val) if isinstance(_total_val, int) else 0
                    # Use task-specific logging if part of multi-task
                    _task_total_val = (
                        ev.data.get("task_total") if isinstance(ev.data, dict) else None
                    )
                    task_total = int(_task_total_val) if isinstance(_task_total_val, int) else 1
                    # Mark images phase as complete for interpolation
                    self._current_phase_key = (
                        "phase_write_start"  # advance to next phase after images
                    )
                    self._current_images_progress = None
                    self._update_interpolated_progress()
                    if task_total > 1:
                        _task_idx_val = (
                            ev.data.get("task_idx") if isinstance(ev.data, dict) else None
                        )
                        task_idx = int(_task_idx_val) if isinstance(_task_idx_val, int) else 0
                        task_id = f"Task {task_idx}/{task_total}"
                        # Ensure the initial download line exists for this task
                        if task_id not in self._images_dl_logged_tasks:
                            self._images_dl_logged_tasks.add(task_id)
                            self.log_panel.appendTaskLog(
                                task_id, f"Downloading images: {total} images"
                            )
                        self.log_panel.appendTaskLog(task_id, f"Images downloaded: {total} images")
                    else:
                        # Ensure the initial download line exists for single-task runs
                        if not self._images_dl_logged:
                            self._images_dl_logged = True
                            self.log_info(f"Downloading images: {total} images")
                        self.log_success(f"Images downloaded: {total} images")
                elif ev.key == "convert_shared_browser_started":
                    self.log_info(self.translator.t("convert_shared_browser_started"))
                elif ev.key == "shared_browser_disabled_for_handler" and ev.data:
                    handler = ev.data.get("handler") if isinstance(ev.data, dict) else ""
                    self.log_info(
                        self.translator.t("shared_browser_disabled_for_handler", handler=handler)
                    )
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
                    self._progress_completed_urls = max(0, completed)
                    self._progress_total_urls = max(self._progress_total_urls, total)
                    # On discrete step, show the exact overall progress without interpolation
                    progress_value = int((completed / total) * 100) if total and total > 0 else 0
                    self.command_panel.set_progress(
                        progress_value,
                        self.translator.t(
                            "progress_text_simple",
                            completed=completed,
                            total=total,
                            percent=progress_value,
                        ),
                    )
                    # Reset intra-task phase state for the next task
                    self._current_phase_key = None
                    self._current_images_progress = None
                else:
                    current = self.command_panel.progress.value()
                    self.command_panel.set_progress(current + 1)

            elif ev.kind == "progress_done":
                self.command_panel.set_progress(
                    100,
                    self.translator.t(
                        "convert_progress_done",
                        completed=ev.data.get("completed", 0) if isinstance(ev.data, dict) else 0,
                        total=ev.data.get("total", 0) if isinstance(ev.data, dict) else 0,
                    ),
                )
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
                        self.log_success(message or self.translator.t("progress_completed"))
                else:
                    self.log_success(message or self.translator.t("progress_completed"))
                self.is_running = False
                self.command_panel.setConvertingState(False)

            elif ev.kind == "stopped":
                self.log_warning(message or self.translator.t("convert_stopped"))
                self.is_running = False
                self.command_panel.setConvertingState(False)

            elif ev.kind == "error":
                self.log_error(message or self.translator.t("progress_error"))
                self.is_running = False
                self.command_panel.setConvertingState(False)

        except Exception as e:
            self.log_error(f"Event handler error: {e}")

    def _update_interpolated_progress(self) -> None:
        """Compute and update interpolated overall progress using intra-task phase state."""
        try:
            total = self._progress_total_urls or 0
            if total <= 0:
                return
            completed = max(0, self._progress_completed_urls)
            # Compute base fraction from completed tasks
            base_fraction = completed / total
            # Compute intra-task fraction contribution
            phase_fraction = 0.0
            if self._current_phase_key:
                phases = self._phase_order
                num_phases = len(phases)
                # Resolve phase index and within-phase progress
                if self._current_phase_key == "phase_images" and self._current_images_progress:
                    phase_index = (
                        phases.index("phase_images") if "phase_images" in phases else num_phases - 2
                    )
                    img_idx, img_total = self._current_images_progress
                    within = (img_idx / img_total) if img_total > 0 else 0.0
                else:
                    # For start events, count as reaching the beginning of that phase
                    phase_index = (
                        phases.index(self._current_phase_key)
                        if self._current_phase_key in phases
                        else 0
                    )
                    within = 0.0
                # Each phase contributes equally within the next 1/total slice
                phase_fraction = ((phase_index + within) / num_phases) / max(1, total)
            # Combine and clamp
            overall_fraction = min(1.0, base_fraction + phase_fraction)
            value = int(overall_fraction * 100)
            label_total = max(total, 1)
            # Friendly interpolated text while in-flight
            if self._current_phase_key == "phase_images" and self._current_images_progress:
                img_idx, img_total = self._current_images_progress
                self.command_panel.set_progress(
                    value,
                    self.translator.t(
                        "images_progress_text",
                        task_idx=img_idx,
                        task_total=img_total,
                        completed=completed,
                        total=label_total,
                        percent=value,
                    ),
                )
            else:
                phase_map = {
                    "phase_fetch_start": self.translator.t("progress_phase_fetch"),
                    "phase_parse_start": self.translator.t("progress_phase_parse"),
                    "phase_clean_start": self.translator.t("progress_phase_clean"),
                    "phase_convert_start": self.translator.t("progress_phase_convert"),
                    "phase_write_start": self.translator.t("progress_phase_write"),
                }
                phase_text = phase_map.get(
                    self._current_phase_key or "", self.translator.t("progress_processing")
                )
                self.command_panel.set_progress(
                    value,
                    self.translator.t(
                        "progress_text_with_counts",
                        phase=phase_text,
                        completed=completed,
                        total=label_total,
                        percent=value,
                    ),
                )
        except Exception:
            # Non-fatal
            pass

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
        import os as _os
        import platform
        import subprocess

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

            # Note: We do NOT save the restored config to last_state.json
            # This allows users to easily restore their previous config later
            # The default config only affects the current session

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
                if system_lang and system_lang.startswith("zh"):
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

    def _restore_config(self):
        """Restore last configuration via ConfigService."""
        try:
            if not self.config_service.load_session():
                self.log_panel.appendLog("No configuration found to restore")
                return
            config = self.config_service.get_all_config()
            self._apply_state(
                config.get("basic", {})
                | config.get("webpage", {})
                | {"output_dir": config.get("basic", {}).get("output_dir", "")}
            )
            self.log_panel.appendLog("Configuration restored successfully")
        except Exception as e:
            self.log_panel.appendLog(f"Failed to restore configuration: {e}")

    def _import_config(self):
        """Import configuration from file via ConfigService."""
        from PySide6.QtWidgets import QFileDialog

        config_dir = os.path.join(self.root_dir, "data", "config")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", config_dir, "JSON Files (*.json)"
        )
        if filename:
            try:
                if not self.config_service.import_config(filename):
                    raise RuntimeError("Import returned False")
                config = self.config_service.get_all_config()
                self._suppress_change_logs = True
                self._apply_state(
                    config.get("basic", {})
                    | config.get("webpage", {})
                    | {"output_dir": config.get("basic", {}).get("output_dir", "")}
                )
                try:
                    if hasattr(self.webpage_page, "_options_changed_timer"):
                        self.webpage_page._options_changed_timer.stop()
                except Exception:
                    pass
                self._suppress_change_logs = False
                self.log_panel.appendLog(
                    f"Configuration imported from: {os.path.basename(filename)}"
                )
            except Exception as e:
                self.log_panel.appendLog(f"Failed to import configuration: {e}")

    def _export_config(self):
        """Export configuration to file via ConfigService."""
        from PySide6.QtWidgets import QFileDialog

        config_dir = os.path.join(self.root_dir, "data", "config")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", config_dir, "JSON Files (*.json)"
        )
        if filename:
            try:
                # Ensure service reflects current UI state before export
                self._save_config()
                if not self.config_service.export_config(filename):
                    raise RuntimeError("Export returned False")
                self.log_panel.appendLog(f"Configuration exported to: {os.path.basename(filename)}")
            except Exception as e:
                self.log_panel.appendLog(f"Failed to export configuration: {e}")

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
        self.vm.start(
            reqs, out_dir, options, self._on_event_thread_safe, self.signals, self, self.translator
        )

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
            "output_dir": resolve_project_path(state.get("output_dir", ""), self.root_dir),
        }
        self.basic_page.set_config(basic_config)

        # Apply to webpage page
        webpage_config = {
            "use_proxy": state.get("use_proxy", False),
            "ignore_ssl": state.get("ignore_ssl", False),
            "download_images": state.get("download_images", True),
            "filter_site_chrome": state.get("filter_site_chrome", True),
            "use_shared_browser": state.get("use_shared_browser", True),
            "handler_override": state.get("handler_override"),
        }
        self.webpage_page.set_config(webpage_config)

    # StartupManager removed; keep placeholders if needed in future

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
            self.config_service.set_basic_config(
                {"urls": state.get("urls", []), "output_dir": state.get("output_dir", "")}
            )

            self.config_service.set_webpage_config(
                {
                    "use_proxy": state.get("use_proxy", False),
                    "ignore_ssl": state.get("ignore_ssl", False),
                    "download_images": state.get("download_images", True),
                    "filter_site_chrome": state.get("filter_site_chrome", True),
                    "use_shared_browser": state.get("use_shared_browser", True),
                    "handler_override": state.get("handler_override"),
                }
            )

            # Add advanced page settings
            advanced_config = self.advanced_page.get_config()
            self.config_service.set_advanced_config(
                {
                    "language": advanced_config.get("language", "auto"),
                }
            )

            # Save unified session (new-format only)
            self.config_service.save_session()

        except Exception as e:
            self.log_error(f"Failed to save config: {e}")

    def _load_config(self):
        """Load configuration using ConfigService."""
        try:
            # Load unified session (new-format). It's OK if missing.
            self.config_service.load_session()

            # Always sync UI from defaults + session
            self._sync_ui_from_config()

        except Exception as e:
            self.log_error(f"Failed to load config: {e}")

    def _sync_ui_from_config(self):
        """Sync UI display from configuration."""
        try:
            config = self.config_service.get_all_config()

            # Update basic page
            basic_config = config["basic"]
            # Resolve project-relative paths so UI holds absolute paths for correctness on Windows
            try:
                from markdownall.io.config import resolve_project_path as _resolve

                od = basic_config.get("output_dir", "")
                if od:
                    basic_config["output_dir"] = _resolve(od, self.root_dir)
                else:
                    basic_config["output_dir"] = self.output_dir_var
            except Exception:
                # Fallback to default if resolution fails
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
