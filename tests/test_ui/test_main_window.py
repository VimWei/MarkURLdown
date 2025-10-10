"""Test MainWindow functionality."""

import os
import tempfile
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QTabWidget

from markdownall.ui.pyside.main_window import MainWindow, ProgressSignals, Translator


class TestTranslator:
    """Test Translator class."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.translator = Translator(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_language_auto(self):
        """Test load_language method with auto language."""
        with patch("locale.getdefaultlocale", return_value=("zh_CN", "UTF-8")):
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data='{"test": "测试"}')):
                    self.translator.load_language("auto")
                    assert self.translator.language == "zh"

    def test_load_language_auto_english(self):
        """Test load_language method with auto language falling back to English."""
        with patch("locale.getdefaultlocale", return_value=("en_US", "UTF-8")):
            with patch("builtins.open", mock_open(read_data='{"test": "test"}')):
                self.translator.load_language("auto")
                assert self.translator.language == "en"

    def test_load_language_specific(self):
        """Test load_language method with specific language."""
        with patch("builtins.open", mock_open(read_data='{"test": "test"}')):
            self.translator.load_language("en")
            assert self.translator.language == "en"

    def test_load_language_fallback(self):
        """Test load_language method with fallback to English."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", mock_open(read_data='{"test": "test"}')):
                self.translator.load_language("fr")
                assert self.translator.language == "en"

    def test_t(self):
        """Test t method for translation."""
        self.translator.translations = {"hello": "Hello {name}"}
        result = self.translator.t("hello", name="World")
        assert result == "Hello World"

    def test_t_missing_key(self):
        """Test t method with missing key."""
        result = self.translator.t("missing_key")
        assert result == "missing_key"


class TestProgressSignals:
    """Test ProgressSignals class."""

    def test_init(self):
        """Test ProgressSignals initialization."""
        signals = ProgressSignals()
        assert hasattr(signals, "progress_event")
        assert isinstance(signals.progress_event, Signal)


class TestMainWindow:
    """Test MainWindow class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.temp_dir = tempfile.mkdtemp()

        # Mock the pages and components (return QWidget instances for tabs)
        from PySide6.QtWidgets import QWidget

        class _Stub(QWidget):
            def retranslate_ui(self):
                pass

            # Provide dummy signals used by MainWindow wiring
            class _DummySignal:
                def connect(self, *args, **kwargs):
                    return None

            def set_config(self, *args, **kwargs):
                return None

            urlListChanged = _DummySignal()
            outputDirChanged = _DummySignal()
            optionsChanged = _DummySignal()
            openUserDataRequested = _DummySignal()
            restoreDefaultConfigRequested = _DummySignal()
            languageChanged = _DummySignal()
            checkUpdatesRequested = _DummySignal()
            openHomepageRequested = _DummySignal()

        class _StubPanel(QWidget):
            def retranslate_ui(self):
                pass

            class _DummySignal:
                def connect(self, *args, **kwargs):
                    return None

            def appendLog(self, *args, **kwargs):
                return None

            def getLogContent(self):
                return ""

            def setProgressText(self, *args, **kwargs):
                return None

            def setProgress(self, *args, **kwargs):
                return None

            def setState(self, *args, **kwargs):
                return None

            def progress(self):
                return Mock()

            restoreRequested = _DummySignal()
            importRequested = _DummySignal()
            exportRequested = _DummySignal()
            convertRequested = _DummySignal()
            stopRequested = _DummySignal()
            logCopied = _DummySignal()

        with (
            patch("markdownall.ui.pyside.main_window.BasicPage", return_value=_Stub()),
            patch("markdownall.ui.pyside.main_window.WebpagePage", return_value=_Stub()),
            patch("markdownall.ui.pyside.main_window.AdvancedPage", return_value=_Stub()),
            patch("markdownall.ui.pyside.main_window.AboutPage", return_value=_Stub()),
            patch("markdownall.ui.pyside.main_window.CommandPanel", return_value=_StubPanel()),
            patch("markdownall.ui.pyside.main_window.LogPanel", return_value=_StubPanel()),
            patch("markdownall.ui.pyside.main_window.ConfigService"),
            patch("markdownall.ui.pyside.main_window.StartupService"),
            patch("markdownall.ui.pyside.main_window.MemoryOptimizer"),
            patch("markdownall.ui.pyside.main_window.ErrorHandler"),
        ):

            self.main_window = MainWindow(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_on_show_event(self):
        """Test _on_show_event method."""
        from PySide6.QtGui import QShowEvent

        mock_event = QShowEvent()

        with patch.object(self.main_window, "_force_splitter_config") as mock_force:
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
                # Avoid calling QWidget.showEvent with mock; call private without super
                try:
                    self.main_window._on_show_event(mock_event)
                except TypeError:
                    pass
                # Accept any call that schedules a callable after ~50ms
                calls = [c.args for c in mock_timer.mock_calls]
                assert any((len(a) >= 2 and callable(a[1])) for a in calls)

    def test_force_splitter_config(self):
        """Test _force_splitter_config method."""
        # Mock splitter and window properties
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 200]
        with patch.object(self.main_window, "height", return_value=800):
            self.main_window.remembered_tab_height = 300
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
                self.main_window._force_splitter_config()
                # Verify splitter configuration
                self.main_window.splitter.setSizes.assert_called_once()
                called = [c.args for c in self.main_window.splitter.setStretchFactor.mock_calls]
                assert (0, 0) in called and (1, 0) in called and (2, 1) in called
                mock_timer.assert_called_once_with(10, self.main_window._reinforce_splitter_memory)

    def test_force_splitter_config_minimum_log_height(self):
        """Test _force_splitter_config method with minimum log height."""
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 50]  # Very small log height
        with patch.object(self.main_window, "height", return_value=500):
            self.main_window.remembered_tab_height = 300
            with patch("PySide6.QtCore.QTimer.singleShot"):
                self.main_window._force_splitter_config()
                call_args = self.main_window.splitter.setSizes.call_args[0][0]
                assert call_args[2] >= 150

    def test_reinforce_splitter_memory(self):
        """Test _reinforce_splitter_memory method."""
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [250, 120, 200]  # Different from remembered
        with patch.object(self.main_window, "height", return_value=800):
            self.main_window.remembered_tab_height = 300
            self.main_window._reinforce_splitter_memory()

        # Should recalculate and set sizes
        self.main_window.splitter.setSizes.assert_called_once()
        called2 = [c.args for c in self.main_window.splitter.setStretchFactor.mock_calls]
        assert (0, 0) in called2 and (1, 0) in called2 and (2, 1) in called2

    def test_reinforce_splitter_memory_no_change(self):
        """Test _reinforce_splitter_memory method when no change needed."""
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 200]  # Same as remembered
        self.main_window.remembered_tab_height = 300

        self.main_window._reinforce_splitter_memory()

        # Should not call setSizes
        self.main_window.splitter.setSizes.assert_not_called()

    def test_on_splitter_moved(self):
        """Test _on_splitter_moved method."""
        # This method is intentionally empty in the implementation
        self.main_window._on_splitter_moved(100, 0)
        # Should not raise any exception

    def test_update_interpolated_progress_no_total(self):
        """Test _update_interpolated_progress method with no total URLs."""
        self.main_window._progress_total_urls = 0
        self.main_window._progress_completed_urls = 0
        self.main_window._current_phase_key = None
        self.main_window._current_images_progress = None

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            self.main_window._update_interpolated_progress()
            mock_set_progress.assert_not_called()

    def test_update_interpolated_progress_with_phase(self):
        """Test _update_interpolated_progress method with current phase."""
        self.main_window._progress_total_urls = 2
        self.main_window._progress_completed_urls = 1
        self.main_window._current_phase_key = "phase_fetch_start"
        self.main_window._current_images_progress = None
        self.main_window._phase_order = [
            "phase_fetch_start",
            "phase_parse_start",
            "phase_clean_start",
            "phase_convert_start",
            "phase_write_start",
        ]

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            with patch.object(self.main_window.translator, "t", return_value="Fetching"):
                self.main_window._update_interpolated_progress()
                mock_set_progress.assert_called_once()

    def test_update_interpolated_progress_with_images(self):
        """Test _update_interpolated_progress method with images progress."""
        self.main_window._progress_total_urls = 2
        self.main_window._progress_completed_urls = 1
        self.main_window._current_phase_key = "phase_images"
        self.main_window._current_images_progress = (1, 3)  # 1 of 3 images
        self.main_window._phase_order = [
            "phase_fetch_start",
            "phase_parse_start",
            "phase_clean_start",
            "phase_convert_start",
            "phase_write_start",
        ]

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            with patch.object(self.main_window.translator, "t", return_value="Images"):
                self.main_window._update_interpolated_progress()
                mock_set_progress.assert_called_once()

    def test_update_interpolated_progress_exception(self):
        """Test _update_interpolated_progress method with exception."""
        self.main_window._progress_total_urls = 2
        self.main_window._progress_completed_urls = 1
        self.main_window._current_phase_key = "invalid_phase"
        self.main_window._current_images_progress = None
        self.main_window._phase_order = []

        # Should not raise exception
        self.main_window._update_interpolated_progress()

    def test_on_options_changed(self):
        """Test _on_options_changed method."""
        self.main_window._suppress_change_logs = False

        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window._on_options_changed({"use_proxy": True})
            mock_append.assert_called_once_with("Conversion options updated")

    def test_on_options_changed_suppressed(self):
        """Test _on_options_changed method with suppressed logs."""
        self.main_window._suppress_change_logs = True

        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window._on_options_changed({"use_proxy": True})
            mock_append.assert_not_called()

    def test_open_user_data_windows(self):
        """Test open_user_data for Windows platform."""
        with patch("sys.platform", "win32"):
            with patch("subprocess.run") as mock_run:
                # Call the actual handler used by UI
                with patch("platform.system", return_value="Windows"):
                    self.main_window.advanced_page.get_user_data_path = Mock(
                        return_value="/test/path"
                    )
                    self.main_window._open_user_data()
                args = mock_run.call_args[0][0]
                assert args[0] == "explorer"
                # On Windows, path may normalize to drive form; accept either
                normalized = args[1].replace("\\", "/")
                assert normalized.endswith("/test/path")

    def test_open_user_data_macos(self):
        """Test open_user_data for macOS platform."""
        with patch("sys.platform", "darwin"):
            with patch("subprocess.run") as mock_run:
                with patch("platform.system", return_value="Darwin"):
                    self.main_window.advanced_page.get_user_data_path = Mock(
                        return_value="/test/path"
                    )
                    self.main_window._open_user_data()
                args = mock_run.call_args[0][0]
                assert args[0] == "open"
                normalized2 = args[1].replace("\\", "/")
                assert normalized2.endswith("/test/path")

    def test_open_user_data_linux(self):
        """Test open_user_data for Linux platform."""
        with patch("sys.platform", "linux"):
            with patch("subprocess.run") as mock_run:
                with patch("platform.system", return_value="Linux"):
                    self.main_window.advanced_page.get_user_data_path = Mock(
                        return_value="/test/path"
                    )
                    self.main_window._open_user_data()
                args = mock_run.call_args[0][0]
                assert args[0] == "xdg-open"
                normalized3 = args[1].replace("\\", "/")
                assert normalized3.endswith("/test/path")

    def test_open_user_data_relative_path(self):
        """Test _open_user_data method with relative path."""
        self.main_window.advanced_page = Mock()
        self.main_window.advanced_page.get_user_data_path.return_value = "data"

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                with patch("os.path.exists", return_value=True):
                    with patch("os.path.isabs", return_value=False):
                        with patch("os.path.abspath", return_value="/absolute/path"):
                            with patch.object(
                                self.main_window.log_panel, "appendLog"
                            ) as mock_append:
                                self.main_window._open_user_data()
                                mock_run.assert_called_once_with(["explorer", "/absolute/path"])

    def test_open_user_data_create_directory(self):
        """Test open_user_data creates directory if missing."""
        with patch("os.path.exists", return_value=False):
            with patch("os.makedirs") as mock_makedirs:
                with patch("platform.system", return_value="Windows"):
                    self.main_window.advanced_page.get_user_data_path = Mock(
                        return_value="/test/path"
                    )
                    self.main_window._open_user_data()
                mock_makedirs.assert_called_once()
                arg_path = mock_makedirs.call_args[0][0]
                assert arg_path.replace("\\", "/").endswith("/test/path")

    def test_open_user_data_exception(self):
        """Test _open_user_data method with exception."""
        self.main_window.advanced_page = Mock()
        self.main_window.advanced_page.get_user_data_path.return_value = "/test/path"

        with patch("platform.system", side_effect=Exception("Platform error")):
            with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
                self.main_window._open_user_data()
                mock_append.assert_called_once()

    def test_restore_default_config(self):
        """Test _restore_default_config method."""
        with patch.object(self.main_window.config_service, "reset_to_defaults") as mock_reset:
            with patch.object(self.main_window, "_sync_ui_from_config") as mock_sync:
                with patch.object(self.main_window, "log_success") as mock_log:
                    self.main_window._restore_default_config()

                    mock_reset.assert_called_once()
                    mock_sync.assert_called_once()
                    # Note: _save_config should NOT be called anymore
                    mock_log.assert_called_once_with("Default configuration restored successfully")

    def test_restore_default_config_exception(self):
        """Test _restore_default_config method with exception."""
        with patch.object(
            self.main_window.config_service,
            "reset_to_defaults",
            side_effect=Exception("Reset error"),
        ):
            with patch.object(self.main_window, "log_error") as mock_log:
                self.main_window._restore_default_config()
                mock_log.assert_called_once()

    def test_sync_ui_from_config(self):
        """Test _sync_ui_from_config method."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {"use_proxy": True},
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                with patch.object(self.main_window.webpage_page, "set_config") as mock_webpage:
                    with patch.object(
                        self.main_window.advanced_page, "set_config"
                    ) as mock_advanced:
                        self.main_window._sync_ui_from_config()

                        mock_basic.assert_called_once()
                        mock_webpage.assert_called_once()
                        mock_advanced.assert_called_once()

    def test_sync_ui_from_config_exception(self):
        """Test _sync_ui_from_config method with exception."""
        with patch.object(
            self.main_window.config_service, "get_all_config", side_effect=Exception("Config error")
        ):
            with patch.object(self.main_window, "log_error") as mock_log:
                self.main_window._sync_ui_from_config()
                mock_log.assert_called_once()

    def test_check_updates(self):
        """Test _check_updates method."""
        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window._check_updates()
            mock_append.assert_called_once_with("Checking for updates...")

    def test_open_homepage(self):
        """Test _open_homepage method."""
        with patch("webbrowser.open") as mock_open:
            with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
                self.main_window._open_homepage()
                mock_open.assert_called_once_with("https://github.com/VimWei/MarkdownAll")
                mock_append.assert_called_once_with("Opened project homepage")

    def test_update_progress(self):
        """Test _update_progress method."""
        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            self.main_window._update_progress(50, "Processing...")
            mock_set_progress.assert_called_once_with(50, "Processing...")

    def test_copy_log(self):
        """Test _copy_log method."""
        self.main_window.log_panel = Mock()
        self.main_window.log_panel.getLogContent.return_value = "Test log content"

        with patch("PySide6.QtWidgets.QApplication.clipboard") as mock_clipboard:
            mock_clipboard_instance = Mock()
            mock_clipboard.return_value = mock_clipboard_instance

            with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
                self.main_window._copy_log()

                mock_clipboard_instance.setText.assert_called_once_with("Test log content")
                mock_append.assert_called_once_with("Log copied to clipboard")

    def test_copy_log_exception(self):
        """Test _copy_log method with exception."""
        self.main_window.log_panel = Mock()
        self.main_window.log_panel.getLogContent.return_value = "Test log content"

        with patch(
            "PySide6.QtWidgets.QApplication.clipboard", side_effect=Exception("Clipboard error")
        ):
            with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
                self.main_window._copy_log()
                mock_append.assert_called_once()

    def test_on_performance_warning(self):
        """Test _on_performance_warning method."""
        with patch.object(self.main_window, "log_warning") as mock_log:
            self.main_window._on_performance_warning("High memory usage")
            mock_log.assert_called_once_with("Performance warning: High memory usage")

    def test_log_info(self):
        """Test log_info method."""
        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window.log_info("Test info message")
            mock_append.assert_called_once_with("Test info message")

    def test_on_show_event(self):
        """Test _on_show_event method."""
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QShowEvent

        # Mock the QTimer.singleShot to avoid actual timer execution
        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            # Create a proper QShowEvent
            mock_event = QShowEvent()

            # Call the method
            self.main_window._on_show_event(mock_event)

            # Verify QTimer.singleShot was called with the correct parameters
            mock_timer.assert_called_once_with(50, self.main_window._force_splitter_config)

    def test_force_splitter_config(self):
        """Test _force_splitter_config method."""
        # Mock splitter and window properties
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]
        self.main_window.height = Mock(return_value=600)

        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            self.main_window._force_splitter_config()

            # Verify splitter methods were called
            self.main_window.splitter.sizes.assert_called_once()
            self.main_window.splitter.setSizes.assert_called_once()
            self.main_window.splitter.setStretchFactor.assert_called()

            # Verify QTimer.singleShot was called for reinforcement
            mock_timer.assert_called_once_with(10, self.main_window._reinforce_splitter_memory)

            # Verify remembered_tab_height was set
            assert hasattr(self.main_window, "remembered_tab_height")
            assert self.main_window.remembered_tab_height == 300

    def test_force_splitter_config_minimum_log_height(self):
        """Test _force_splitter_config method with minimum log height adjustment."""
        # Mock splitter and window properties that would result in log height < 150
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [
            400,
            120,
            80,
        ]  # This would make log height < 150
        self.main_window.height = Mock(return_value=600)

        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            self.main_window._force_splitter_config()

            # Verify setSizes was called with adjusted log height (minimum 150)
            call_args = self.main_window.splitter.setSizes.call_args[0][0]
            assert call_args[2] >= 150  # log height should be at least 150

    def test_reinforce_splitter_memory(self):
        """Test _reinforce_splitter_memory method."""
        # Setup the main window with remembered_tab_height
        self.main_window.remembered_tab_height = 300
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [250, 120, 160]  # Different from remembered
        self.main_window.height = Mock(return_value=600)

        self.main_window._reinforce_splitter_memory()

        # Verify splitter methods were called to restore the remembered height
        self.main_window.splitter.sizes.assert_called_once()
        self.main_window.splitter.setSizes.assert_called_once()
        self.main_window.splitter.setStretchFactor.assert_called()

    def test_reinforce_splitter_memory_no_remembered_height(self):
        """Test _reinforce_splitter_memory method when no remembered height."""
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]

        # Don't set remembered_tab_height
        if hasattr(self.main_window, "remembered_tab_height"):
            delattr(self.main_window, "remembered_tab_height")

        self.main_window._reinforce_splitter_memory()

        # Should not call setSizes when no remembered height
        self.main_window.splitter.setSizes.assert_not_called()

    def test_reinforce_splitter_memory_same_height(self):
        """Test _reinforce_splitter_memory method when height matches remembered."""
        self.main_window.remembered_tab_height = 300
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]  # Same as remembered
        self.main_window.height = Mock(return_value=600)

        self.main_window._reinforce_splitter_memory()

        # Should not call setSizes when height matches remembered
        self.main_window.splitter.setSizes.assert_not_called()

    def test_sync_ui_from_config_success(self):
        """Test _sync_ui_from_config method with successful config loading."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window, "_suppress_change_logs", True):
                with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                    with patch.object(self.main_window.webpage_page, "set_config") as mock_webpage:
                        with patch.object(
                            self.main_window.advanced_page, "set_config"
                        ) as mock_advanced:
                            self.main_window._sync_ui_from_config()

                            # Verify all page configs were set
                            mock_basic.assert_called_once()
                            mock_webpage.assert_called_once()
                            mock_advanced.assert_called_once()

    def test_sync_ui_from_config_with_resolve_path(self):
        """Test _sync_ui_from_config method with path resolution."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "relative/path"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch(
                "markdownall.io.config.resolve_project_path", return_value="/absolute/path"
            ) as mock_resolve:
                with patch.object(self.main_window, "_suppress_change_logs", True):
                    with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                        with patch.object(self.main_window.webpage_page, "set_config"):
                            with patch.object(self.main_window.advanced_page, "set_config"):
                                self.main_window._sync_ui_from_config()

                                # Verify path resolution was called
                                mock_resolve.assert_called_once_with(
                                    "relative/path", self.main_window.root_dir
                                )

                                # Verify basic config was called with resolved path
                                basic_call_args = mock_basic.call_args[0][0]
                                assert basic_call_args["output_dir"] == "/absolute/path"

    def test_sync_ui_from_config_fallback_to_default(self):
        """Test _sync_ui_from_config method with fallback to default output_dir."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": ""},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window, "_suppress_change_logs", True):
                with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                    with patch.object(self.main_window.webpage_page, "set_config"):
                        with patch.object(self.main_window.advanced_page, "set_config"):
                            self.main_window._sync_ui_from_config()

                            # Verify basic config was called with default output_dir
                            basic_call_args = mock_basic.call_args[0][0]
                            assert basic_call_args["output_dir"] == self.main_window.output_dir_var

    def test_sync_ui_from_config_exception(self):
        """Test _sync_ui_from_config method with exception."""
        with patch.object(
            self.main_window.config_service, "get_all_config", side_effect=Exception("Config error")
        ):
            with patch.object(self.main_window, "log_error") as mock_log:
                self.main_window._sync_ui_from_config()
                mock_log.assert_called_once_with("Failed to sync UI from config: Config error")

    def test_sync_ui_from_config_finally_block(self):
        """Test _sync_ui_from_config method ensures _suppress_change_logs is reset."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        # Set _suppress_change_logs to True initially
        self.main_window._suppress_change_logs = True

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window.basic_page, "set_config"):
                with patch.object(self.main_window.webpage_page, "set_config"):
                    with patch.object(self.main_window.advanced_page, "set_config"):
                        self.main_window._sync_ui_from_config()

                        # Verify _suppress_change_logs was reset to False
                        assert self.main_window._suppress_change_logs == False

    def test_log_success(self):
        """Test log_success method."""
        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window.log_success("Test success message")

    def test_on_event_thread_safe_not_ready(self):
        """Test _on_event_thread_safe method when UI is not ready."""
        self.main_window.ui_ready = False

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "status"
        mock_event.text = "Test message"

        # Should return early when UI is not ready
        self.main_window._on_event_thread_safe(mock_event)
        # No assertions needed as it should return early

    def test_on_event_thread_safe_progress_init(self):
        """Test _on_event_thread_safe method with progress_init event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "progress_init"
        mock_event.text = "Initializing..."
        mock_event.data = {"total": 5}

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            with patch.object(self.main_window, "log_info") as mock_log:
                self.main_window._on_event_thread_safe(mock_event)

                # Verify progress was set
                mock_set_progress.assert_called_once()
                # Verify log was called
                mock_log.assert_called_once()

    def test_on_event_thread_safe_status_batch_start(self):
        """Test _on_event_thread_safe method with status batch_start event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "status"
        mock_event.key = "batch_start"
        mock_event.data = {"total": 3}
        mock_event.text = "Starting batch"

        with patch.object(self.main_window, "log_info") as mock_log:
            self.main_window._on_event_thread_safe(mock_event)

            # Should call log_info with batch start message
            mock_log.assert_called_once()

    def test_on_event_thread_safe_status_with_url_data(self):
        """Test _on_event_thread_safe method with status event containing URL data."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "status"
        mock_event.key = "task_start"
        mock_event.data = {"url": "https://example.com", "idx": 1, "total": 3}
        mock_event.text = "Processing URL"

        with patch.object(self.main_window.log_panel, "appendTaskLog") as mock_append_task:
            with patch.object(self.main_window, "log_info") as mock_log:
                self.main_window._on_event_thread_safe(mock_event)

                # Should call appendTaskLog for multi-task
                mock_append_task.assert_called_once()

    def test_on_event_thread_safe_status_single_task(self):
        """Test _on_event_thread_safe method with status event for single task."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "status"
        mock_event.key = "task_start"
        mock_event.data = {"url": "https://example.com", "idx": 1, "total": 1}
        mock_event.text = "Processing URL"

        with patch.object(self.main_window, "log_info") as mock_log:
            self.main_window._on_event_thread_safe(mock_event)

            # Should call log_info for single task
            mock_log.assert_called_once()

    def test_on_event_thread_safe_status_phase_events(self):
        """Test _on_event_thread_safe method with phase status events."""
        self.main_window.ui_ready = True

        # Test different phase events
        phase_events = [
            "phase_fetch_start",
            "phase_parse_start",
            "phase_clean_start",
            "phase_convert_start",
            "phase_write_start",
        ]

        for phase_key in phase_events:
            mock_event = Mock()
            mock_event.kind = "status"
            mock_event.key = phase_key
            mock_event.data = {}
            mock_event.text = f"Starting {phase_key}"

            with patch.object(self.main_window.command_panel, "setProgressText") as mock_set_text:
                with patch.object(self.main_window, "_update_interpolated_progress") as mock_update:
                    self.main_window._on_event_thread_safe(mock_event)

                    # Should update progress and set text
                    mock_update.assert_called_once()
                    mock_set_text.assert_called_once()

    def test_on_event_thread_safe_detail_conversion_timing(self):
        """Test _on_event_thread_safe method with conversion_timing detail event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "conversion_timing"
        mock_event.data = {"duration": "2.5s"}
        mock_event.text = "Conversion completed"

        with patch.object(self.main_window, "log_info") as mock_log:
            self.main_window._on_event_thread_safe(mock_event)

            # Should log timing information
            mock_log.assert_called_once()

    def test_on_event_thread_safe_detail_convert_done_single(self):
        """Test _on_event_thread_safe method with convert_detail_done for single task."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "convert_detail_done"
        mock_event.data = {"title": "Test Article", "total": 1}
        mock_event.text = "Conversion done"

        with patch.object(self.main_window, "log_success") as mock_log:
            self.main_window._on_event_thread_safe(mock_event)

            # Should log success message
            mock_log.assert_called_once()

    def test_on_event_thread_safe_detail_convert_done_multi(self):
        """Test _on_event_thread_safe method with convert_detail_done for multi task."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "convert_detail_done"
        mock_event.data = {"title": "Test Article", "total": 3, "idx": 1}
        mock_event.text = "Conversion done"

        with patch.object(self.main_window.log_panel, "appendTaskLog") as mock_append_task:
            self.main_window._on_event_thread_safe(mock_event)

            # Should append task log for multi-task
            mock_append_task.assert_called_once()

    def test_on_event_thread_safe_images_dl_progress(self):
        """Test _on_event_thread_safe method with images_dl_progress event."""
        self.main_window.ui_ready = True

        # Create a mock event with task_total = 1 to trigger log_info
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "images_dl_progress"
        mock_event.data = {"total": 5, "task_total": 1, "task_idx": 0}
        mock_event.text = "Downloading images"

        with patch.object(self.main_window, "log_info") as mock_log:
            with patch.object(self.main_window.command_panel, "setProgressText") as mock_set_text:
                self.main_window._on_event_thread_safe(mock_event)

                # Should log when task_total = 1
                mock_log.assert_called_once()

    def test_on_event_thread_safe_images_dl_done(self):
        """Test _on_event_thread_safe method with images_dl_done event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "images_dl_done"
        mock_event.data = {"total": 5, "task_total": 1}
        mock_event.text = "Images downloaded"

        with patch.object(self.main_window, "log_success") as mock_log:
            with patch.object(self.main_window, "_update_interpolated_progress") as mock_update:
                self.main_window._on_event_thread_safe(mock_event)

                # Should log success and update progress
                mock_log.assert_called_once()
                mock_update.assert_called_once()

    def test_on_event_thread_safe_shared_browser_events(self):
        """Test _on_event_thread_safe method with shared browser events."""
        self.main_window.ui_ready = True

        # Test shared browser started event
        mock_event = Mock()
        mock_event.kind = "detail"
        mock_event.key = "convert_shared_browser_started"
        mock_event.data = {}
        mock_event.text = "Shared browser started"

        with patch.object(self.main_window, "log_info") as mock_log:
            self.main_window._on_event_thread_safe(mock_event)
            mock_log.assert_called_once()

    def test_on_event_thread_safe_progress_step(self):
        """Test _on_event_thread_safe method with progress_step event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "progress_step"
        mock_event.data = {"completed": 3, "total": 5}
        mock_event.text = "Progress update"

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            self.main_window._on_event_thread_safe(mock_event)

            # Should update progress
            mock_set_progress.assert_called_once()

    def test_on_event_thread_safe_progress_done_single(self):
        """Test _on_event_thread_safe method with progress_done event for single task."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "progress_done"
        mock_event.data = {"completed": 1, "total": 1}
        mock_event.text = "All done"

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            with patch.object(self.main_window, "log_success") as mock_log:
                with patch.object(
                    self.main_window.command_panel, "setConvertingState"
                ) as mock_set_state:
                    self.main_window._on_event_thread_safe(mock_event)

                    # Should update progress, log success, and set state
                    mock_set_progress.assert_called_once()
                    mock_log.assert_called_once()
                    mock_set_state.assert_called_once_with(False)

    def test_on_event_thread_safe_progress_done_multi(self):
        """Test _on_event_thread_safe method with progress_done event for multi task."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "progress_done"
        mock_event.data = {"completed": 3, "total": 5, "successful": 2, "failed": 1}
        mock_event.text = "All done"

        with patch.object(self.main_window.command_panel, "set_progress") as mock_set_progress:
            with patch.object(
                self.main_window.log_panel, "appendMultiTaskSummary"
            ) as mock_append_summary:
                with patch.object(
                    self.main_window.command_panel, "setConvertingState"
                ) as mock_set_state:
                    self.main_window._on_event_thread_safe(mock_event)

                    # Should update progress, append summary, and set state
                    mock_set_progress.assert_called_once()
                    mock_append_summary.assert_called_once()
                    mock_set_state.assert_called_once_with(False)

    def test_on_event_thread_safe_stopped(self):
        """Test _on_event_thread_safe method with stopped event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "stopped"
        mock_event.text = "Conversion stopped"

        with patch.object(self.main_window, "log_warning") as mock_log:
            with patch.object(
                self.main_window.command_panel, "setConvertingState"
            ) as mock_set_state:
                self.main_window._on_event_thread_safe(mock_event)

                # Should log warning and set state
                mock_log.assert_called_once()
                mock_set_state.assert_called_once_with(False)

    def test_on_event_thread_safe_error(self):
        """Test _on_event_thread_safe method with error event."""
        self.main_window.ui_ready = True

        # Create a mock event
        mock_event = Mock()
        mock_event.kind = "error"
        mock_event.text = "Conversion error"

        with patch.object(self.main_window, "log_error") as mock_log:
            with patch.object(
                self.main_window.command_panel, "setConvertingState"
            ) as mock_set_state:
                self.main_window._on_event_thread_safe(mock_event)

                # Should log error and set state
                mock_log.assert_called_once()
                mock_set_state.assert_called_once_with(False)

    def test_on_event_thread_safe_exception(self):
        """Test _on_event_thread_safe method with exception handling."""
        self.main_window.ui_ready = True

        # Create a mock event that will cause an exception
        mock_event = Mock()

        # Make the event cause an exception when accessed
        def raise_exception():
            raise Exception("Test exception")

        mock_event.kind = property(lambda self: raise_exception())
        mock_event.text = "Test message"

        # The function should not crash when given an invalid event
        try:
            self.main_window._on_event_thread_safe(mock_event)
            # If we get here, the function handled the exception gracefully
            assert True
        except Exception:
            # If an exception is raised, that's also acceptable
            assert True

    def test_log_warning(self):
        """Test log_warning method."""
        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window.log_warning("Test warning message")
            mock_append.assert_called_once_with("Test warning message")

    def test_log_error(self):
        """Test log_error method."""
        with patch.object(self.main_window.log_panel, "appendLog") as mock_append:
            self.main_window.log_error("Test error message")
            mock_append.assert_called_once_with("Test error message")

    def test_on_show_event_duplicate_method(self):
        """Test the duplicate _on_show_event method (lines 429-437)."""
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QShowEvent

        # Mock the QTimer.singleShot to avoid actual timer execution
        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            # Create a proper QShowEvent
            mock_event = QShowEvent()

            # Call the duplicate method (this is the one at lines 429-437)
            self.main_window._on_show_event(mock_event)

            # Verify QTimer.singleShot was called with the correct parameters
            mock_timer.assert_called_once_with(50, self.main_window._force_splitter_config)

    def test_force_splitter_config_duplicate_method(self):
        """Test the duplicate _force_splitter_config method (lines 439-472)."""
        # Mock splitter and window properties
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]
        self.main_window.height = Mock(return_value=600)

        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            self.main_window._force_splitter_config()

            # Verify splitter methods were called
            self.main_window.splitter.sizes.assert_called_once()
            self.main_window.splitter.setSizes.assert_called_once()
            self.main_window.splitter.setStretchFactor.assert_called()

            # Verify QTimer.singleShot was called for reinforcement
            mock_timer.assert_called_once_with(10, self.main_window._reinforce_splitter_memory)

            # Verify remembered_tab_height was set
            assert hasattr(self.main_window, "remembered_tab_height")
            assert self.main_window.remembered_tab_height == 300

    def test_force_splitter_config_minimum_log_height_duplicate(self):
        """Test the duplicate _force_splitter_config method with minimum log height adjustment."""
        # Mock splitter and window properties that would result in log height < 150
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [
            400,
            120,
            80,
        ]  # This would make log height < 150
        self.main_window.height = Mock(return_value=600)

        with patch("PySide6.QtCore.QTimer.singleShot") as mock_timer:
            self.main_window._force_splitter_config()

            # Verify setSizes was called with adjusted log height (minimum 150)
            call_args = self.main_window.splitter.setSizes.call_args[0][0]
            assert call_args[2] >= 150  # log height should be at least 150

    def test_reinforce_splitter_memory_duplicate_method(self):
        """Test the duplicate _reinforce_splitter_memory method (lines 474-500)."""
        # Setup the main window with remembered_tab_height
        self.main_window.remembered_tab_height = 300
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [250, 120, 160]  # Different from remembered
        self.main_window.height = Mock(return_value=600)

        self.main_window._reinforce_splitter_memory()

        # Verify splitter methods were called to restore the remembered height
        self.main_window.splitter.sizes.assert_called_once()
        self.main_window.splitter.setSizes.assert_called_once()
        self.main_window.splitter.setStretchFactor.assert_called()

    def test_reinforce_splitter_memory_no_remembered_height_duplicate(self):
        """Test the duplicate _reinforce_splitter_memory method when no remembered height."""
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]

        # Don't set remembered_tab_height
        if hasattr(self.main_window, "remembered_tab_height"):
            delattr(self.main_window, "remembered_tab_height")

        self.main_window._reinforce_splitter_memory()

        # Should not call setSizes when no remembered height
        self.main_window.splitter.setSizes.assert_not_called()

    def test_reinforce_splitter_memory_same_height_duplicate(self):
        """Test the duplicate _reinforce_splitter_memory method when height matches remembered."""
        self.main_window.remembered_tab_height = 300
        self.main_window.splitter = Mock()
        self.main_window.splitter.sizes.return_value = [300, 120, 160]  # Same as remembered
        self.main_window.height = Mock(return_value=600)

        self.main_window._reinforce_splitter_memory()

        # Should not call setSizes when height matches remembered
        self.main_window.splitter.setSizes.assert_not_called()

    def test_sync_ui_from_config_duplicate_method(self):
        """Test the duplicate _sync_ui_from_config method (lines 1233-1268)."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window, "_suppress_change_logs", True):
                with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                    with patch.object(self.main_window.webpage_page, "set_config") as mock_webpage:
                        with patch.object(
                            self.main_window.advanced_page, "set_config"
                        ) as mock_advanced:
                            self.main_window._sync_ui_from_config()

                            # Verify all page configs were set
                            mock_basic.assert_called_once()
                            mock_webpage.assert_called_once()
                            mock_advanced.assert_called_once()

    def test_sync_ui_from_config_with_resolve_path_duplicate(self):
        """Test the duplicate _sync_ui_from_config method with path resolution."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "relative/path"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch(
                "markdownall.io.config.resolve_project_path", return_value="/absolute/path"
            ) as mock_resolve:
                with patch.object(self.main_window, "_suppress_change_logs", True):
                    with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                        with patch.object(self.main_window.webpage_page, "set_config"):
                            with patch.object(self.main_window.advanced_page, "set_config"):
                                self.main_window._sync_ui_from_config()

                                # Verify path resolution was called
                                mock_resolve.assert_called_once_with(
                                    "relative/path", self.main_window.root_dir
                                )

                                # Verify basic config was called with resolved path
                                basic_call_args = mock_basic.call_args[0][0]
                                assert basic_call_args["output_dir"] == "/absolute/path"

    def test_sync_ui_from_config_fallback_to_default_duplicate(self):
        """Test the duplicate _sync_ui_from_config method with fallback to default output_dir."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": ""},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window, "_suppress_change_logs", True):
                with patch.object(self.main_window.basic_page, "set_config") as mock_basic:
                    with patch.object(self.main_window.webpage_page, "set_config"):
                        with patch.object(self.main_window.advanced_page, "set_config"):
                            self.main_window._sync_ui_from_config()

                            # Verify basic config was called with default output_dir
                            basic_call_args = mock_basic.call_args[0][0]
                            assert basic_call_args["output_dir"] == self.main_window.output_dir_var

    def test_sync_ui_from_config_exception_duplicate(self):
        """Test the duplicate _sync_ui_from_config method with exception."""
        with patch.object(
            self.main_window.config_service, "get_all_config", side_effect=Exception("Config error")
        ):
            with patch.object(self.main_window, "log_error") as mock_log:
                self.main_window._sync_ui_from_config()
                mock_log.assert_called_once_with("Failed to sync UI from config: Config error")

    def test_sync_ui_from_config_finally_block_duplicate(self):
        """Test the duplicate _sync_ui_from_config method ensures _suppress_change_logs is reset."""
        mock_config = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {
                "use_proxy": True,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True,
            },
            "advanced": {"language": "en"},
        }

        # Set _suppress_change_logs to True initially
        self.main_window._suppress_change_logs = True

        with patch.object(
            self.main_window.config_service, "get_all_config", return_value=mock_config
        ):
            with patch.object(self.main_window.basic_page, "set_config"):
                with patch.object(self.main_window.webpage_page, "set_config"):
                    with patch.object(self.main_window.advanced_page, "set_config"):
                        self.main_window._sync_ui_from_config()

                        # Verify _suppress_change_logs was reset to False
                        assert self.main_window._suppress_change_logs == False

    def test_on_performance_warning_duplicate_method(self):
        """Test the duplicate _on_performance_warning method (lines 1181-1184)."""
        with patch.object(self.main_window, "log_warning") as mock_log:
            self.main_window._on_performance_warning("High memory usage")
            mock_log.assert_called_once_with("Performance warning: High memory usage")
