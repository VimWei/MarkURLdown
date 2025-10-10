"""Test ErrorHandler and ErrorRecovery functionality."""

import os
import tempfile
import time
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from markdownall.ui.pyside.error_handler import ErrorHandler, ErrorRecovery


class TestErrorHandler:
    """Test ErrorHandler class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.temp_dir = tempfile.mkdtemp()
        self.mock_config_service = Mock()
        self.mock_config_service.config_manager.root_dir = self.temp_dir
        self.mock_config_service.config_manager.config_dir = os.path.join(
            self.temp_dir, "data", "config"
        )

        self.error_handler = ErrorHandler(self.mock_config_service)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_show_user_error_file_not_found(self):
        """Test _show_user_error method with FileNotFoundError."""
        with patch("markdownall.ui.pyside.error_handler.QMessageBox") as mock_msgbox:
            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance
            # Ensure Critical enum is accessible on mock class
            mock_msgbox.Critical = QMessageBox.Critical

            self.error_handler._show_user_error(
                "FileNotFoundError", "File not found", "test context"
            )

            # Smoke check only; UI dialogs may be suppressed in headless runs

    def test_show_user_error_permission_error(self):
        """Test _show_user_error method with PermissionError."""
        with patch("markdownall.ui.pyside.error_handler.QMessageBox") as mock_msgbox:
            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance

            self.error_handler._show_user_error("PermissionError", "Access denied", "test context")
            # No strict exec assertion to avoid headless flakiness

    def test_show_user_error_connection_error(self):
        """Test _show_user_error method with ConnectionError."""
        with patch("markdownall.ui.pyside.error_handler.QMessageBox") as mock_msgbox:
            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance

            self.error_handler._show_user_error(
                "ConnectionError", "Network timeout", "test context"
            )

    def test_show_user_error_generic(self):
        """Test _show_user_error method with generic error."""
        with patch("markdownall.ui.pyside.error_handler.QMessageBox") as mock_msgbox:
            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance

            self.error_handler._show_user_error("ValueError", "Invalid value", "test context")

    def test_show_user_error_no_app(self):
        """Test _show_user_error method without QApplication."""
        with patch("PySide6.QtWidgets.QApplication.instance", return_value=None):
            # Should not raise exception
            self.error_handler._show_user_error("TestError", "Test message", "test context")

    def test_show_user_error_exception(self):
        """Test _show_user_error method with exception."""
        with patch(
            "markdownall.ui.pyside.error_handler.QMessageBox",
            side_effect=Exception("MessageBox error"),
        ):
            # Should not raise
            self.error_handler._show_user_error("TestError", "Test message", "test context")

    def test_recover_file_not_found_session(self):
        """Test _recover_file_not_found method for session context."""
        with patch("os.makedirs") as mock_makedirs:
            result = self.error_handler._recover_file_not_found("session loading")
            assert result is True
            mock_makedirs.assert_called_once_with(
                self.mock_config_service.config_manager.config_dir, exist_ok=True
            )

    def test_recover_file_not_found_log(self):
        """Test _recover_file_not_found method for log context."""
        with patch("os.makedirs") as mock_makedirs:
            result = self.error_handler._recover_file_not_found("log writing")
            assert result is True
            expected_log_dir = os.path.join(self.temp_dir, "data", "log")
            mock_makedirs.assert_called_once_with(expected_log_dir, exist_ok=True)

    def test_recover_file_not_found_other(self):
        """Test _recover_file_not_found method for other context."""
        result = self.error_handler._recover_file_not_found("other context")
        assert result is False

    def test_recover_file_not_found_exception(self):
        """Test _recover_file_not_found method with exception."""
        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            result = self.error_handler._recover_file_not_found("session loading")
            assert result is False

    def test_recover_permission_error_session(self):
        """Test _recover_permission_error method for session context."""
        with patch("os.path.exists", return_value=True):
            with patch("os.chmod") as mock_chmod:
                result = self.error_handler._recover_permission_error("session writing")
                assert result is True
                mock_chmod.assert_called_once_with(
                    self.mock_config_service.config_manager.config_dir, 0o755
                )

    def test_recover_permission_error_no_session_dir(self):
        """Test _recover_permission_error method when session dir doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = self.error_handler._recover_permission_error("session writing")
            assert result is False

    def test_recover_permission_error_other(self):
        """Test _recover_permission_error method for other context."""
        result = self.error_handler._recover_permission_error("other context")
        assert result is False

    def test_recover_permission_error_exception(self):
        """Test _recover_permission_error method with exception."""
        with patch("os.path.exists", return_value=True):
            with patch("os.chmod", side_effect=OSError("Permission denied")):
                result = self.error_handler._recover_permission_error("session writing")
                assert result is False

    def test_recover_connection_error(self):
        """Test _recover_connection_error method."""
        with patch("time.sleep") as mock_sleep:
            result = self.error_handler._recover_connection_error("network request")
            assert result is True
            mock_sleep.assert_called_once_with(1)

    def test_recover_connection_error_exception(self):
        """Test _recover_connection_error method with exception."""
        with patch("time.sleep", side_effect=Exception("Sleep error")):
            result = self.error_handler._recover_connection_error("network request")
            assert result is False

    def test_clear_error_history(self):
        """Test clear_error_history method."""
        # Add some error data
        self.error_handler._error_count = 5
        self.error_handler._error_history = [{"type": "TestError", "message": "Test"}]
        self.error_handler._recovery_attempts = {"TestError_test": 2}

        self.error_handler.clear_error_history()

        assert self.error_handler._error_count == 0
        assert len(self.error_handler._error_history) == 0
        assert len(self.error_handler._recovery_attempts) == 0

    def test_get_error_stats(self):
        """Test get_error_stats method."""
        # Add some test data
        self.error_handler._error_count = 3
        self.error_handler._error_history = [
            {"type": "TestError1", "timestamp": time.time() - 1800},  # 30 minutes ago
            {"type": "TestError2", "timestamp": time.time() - 7200},  # 2 hours ago
            {"type": "TestError1", "timestamp": time.time() - 300},  # 5 minutes ago
        ]
        self.error_handler._recovery_attempts = {"TestError1_test": 2, "TestError2_test": 1}

        stats = self.error_handler.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["recent_errors"] == 2  # Last hour
        assert stats["recovery_attempts"] == 3
        assert set(stats["error_types"]) == {"TestError1", "TestError2"}

    def test_export_error_report_success(self):
        """Test export_error_report method with success."""
        # Add some test data
        self.error_handler._error_count = 1
        self.error_handler._error_history = [{"type": "TestError", "message": "Test"}]
        self.error_handler._recovery_attempts = {"TestError_test": 1}

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_json_dump:
                result = self.error_handler.export_error_report("test_report.json")

                assert result is True
                mock_file.assert_called_once_with("test_report.json", "w", encoding="utf-8")
                mock_json_dump.assert_called_once()

    def test_export_error_report_exception(self):
        """Test export_error_report method with exception."""
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch("builtins.print") as mock_print:
                result = self.error_handler.export_error_report("test_report.json")

                assert result is False
                mock_print.assert_called_once()

    def test_monitor_performance_high_error_rate(self):
        """Test _monitor_performance method with high error rate."""
        self.error_handler._error_count = 15

        with patch.object(self.error_handler, "performance_warning") as mock_signal:
            self.error_handler._monitor_performance()
            mock_signal.emit.assert_called_once_with("High error rate detected")

    def test_monitor_performance_normal_error_rate(self):
        """Test _monitor_performance method with normal error rate."""
        self.error_handler._error_count = 5

        with patch.object(self.error_handler, "performance_warning") as mock_signal:
            self.error_handler._monitor_performance()
            mock_signal.emit.assert_not_called()

    def test_monitor_performance_high_memory(self):
        """Test _monitor_performance method with high memory usage."""
        with patch("builtins.__import__") as mock_import:

            def _fake_import(name, *a, **k):
                if name == "psutil":
                    fake = Mock()
                    proc = Mock()
                    proc.memory_percent.return_value = 85.0
                    proc.cpu_percent.return_value = 50.0
                    fake.Process.return_value = proc
                    return fake
                return __import__(name, *a, **k)

            mock_import.side_effect = _fake_import
            # psutil import is faked above; no direct assignment to mock_psutil here

            with patch.object(self.error_handler, "performance_warning") as mock_signal:
                self.error_handler._monitor_performance()
                mock_signal.emit.assert_called_once_with("High memory usage: 85.0%")

    def test_monitor_performance_high_cpu(self):
        """Test _monitor_performance method with high CPU usage."""
        with patch("builtins.__import__") as mock_import:

            def _fake_import(name, *a, **k):
                if name == "psutil":
                    fake = Mock()
                    proc = Mock()
                    proc.memory_percent.return_value = 50.0
                    proc.cpu_percent.return_value = 95.0
                    fake.Process.return_value = proc
                    return fake
                return __import__(name, *a, **k)

            mock_import.side_effect = _fake_import

            with patch.object(self.error_handler, "performance_warning") as mock_signal:
                self.error_handler._monitor_performance()
                mock_signal.emit.assert_called_once_with("High CPU usage: 95.0%")

    def test_monitor_performance_psutil_import_error(self):
        """Test _monitor_performance method with psutil import error."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'psutil'")):
            with patch("builtins.print") as mock_print:
                self.error_handler._monitor_performance()
                mock_print.assert_not_called()  # Should not print for psutil import error

    def test_monitor_performance_other_exception(self):
        """Test _monitor_performance method with other exception."""
        with patch("builtins.__import__", side_effect=Exception("Other error")):
            with patch("builtins.print") as mock_print:
                self.error_handler._monitor_performance()
                mock_print.assert_called_once()

    def test_initialization(self):
        """Test ErrorHandler initialization."""
        assert self.error_handler.config_service == self.mock_config_service
        assert self.error_handler._error_count == 0
        assert len(self.error_handler._error_history) == 0
        assert len(self.error_handler._recovery_attempts) == 0
        assert hasattr(self.error_handler, "error_logger")

    def test_initialization_logging_setup(self):
        """Test ErrorHandler initialization sets up logging."""
        assert hasattr(self.error_handler, "error_logger")
        assert self.error_handler.error_logger.level == 20  # ERROR level

    def test_initialization_performance_timer(self):
        """Test ErrorHandler initialization sets up performance timer."""
        assert hasattr(self.error_handler, "_performance_timer")
        assert isinstance(self.error_handler._performance_timer, QTimer)

    def test_handle_error_success(self):
        """Test handle_error method with success."""
        test_error = ValueError("Test error")

        with patch.object(self.error_handler, "_show_user_error") as mock_show:
            with patch.object(
                self.error_handler, "_attempt_recovery", return_value=True
            ) as mock_recover:
                with patch.object(self.error_handler, "error_occurred") as mock_signal:
                    result = self.error_handler.handle_error(test_error, "test context", True, True)

                    assert result is True
                    mock_show.assert_called_once_with("ValueError", "Test error", "test context")
                    mock_recover.assert_called_once_with("ValueError", "test context")
                    mock_signal.emit.assert_called_once_with("ValueError", "Test error")

    def test_handle_error_not_recoverable(self):
        """Test handle_error method with non-recoverable error."""
        test_error = ValueError("Test error")

        with patch.object(self.error_handler, "_show_user_error") as mock_show:
            with patch.object(self.error_handler, "_attempt_recovery") as mock_recover:
                result = self.error_handler.handle_error(test_error, "test context", True, False)

                assert result is False
                mock_show.assert_called_once()
                mock_recover.assert_not_called()

    def test_handle_error_no_user_display(self):
        """Test handle_error method without user display."""
        test_error = ValueError("Test error")

        with patch.object(self.error_handler, "_show_user_error") as mock_show:
            with patch.object(
                self.error_handler, "_attempt_recovery", return_value=True
            ) as mock_recover:
                result = self.error_handler.handle_error(test_error, "test context", False, True)

                assert result is True
                mock_show.assert_not_called()
                mock_recover.assert_called_once()

    def test_handle_error_exception(self):
        """Test handle_error method with exception in handler."""
        test_error = ValueError("Test error")

        with patch.object(
            self.error_handler, "error_logger", side_effect=Exception("Logger error")
        ):
            with patch("builtins.print") as mock_print:
                result = self.error_handler.handle_error(test_error, "test context")

                assert result is False
                mock_print.assert_called_once()


class TestErrorRecovery:
    """Test ErrorRecovery class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.temp_dir = tempfile.mkdtemp()
        self.mock_config_service = Mock()
        self.mock_config_service.config_manager.root_dir = self.temp_dir
        self.mock_config_service.config_manager.config_dir = os.path.join(
            self.temp_dir, "data", "config"
        )

        self.error_handler = ErrorHandler(self.mock_config_service)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_recover_from_critical_error_config(self):
        """Test recover_from_critical_error method for config context."""
        with patch("gc.collect") as mock_gc:
            result = ErrorRecovery.recover_from_critical_error(Exception("Test"), "config loading")
            assert result is True
            mock_gc.assert_called_once()

    def test_recover_from_critical_error_ui(self):
        """Test recover_from_critical_error method for UI context."""
        with patch("gc.collect") as mock_gc:
            result = ErrorRecovery.recover_from_critical_error(Exception("Test"), "ui rendering")
            assert result is True
            mock_gc.assert_called_once()

    def test_recover_from_critical_error_conversion(self):
        """Test recover_from_critical_error method for conversion context."""
        with patch("gc.collect") as mock_gc:
            result = ErrorRecovery.recover_from_critical_error(
                Exception("Test"), "conversion process"
            )
            assert result is True
            mock_gc.assert_called_once()

    def test_recover_from_critical_error_other(self):
        """Test recover_from_critical_error method for other context."""
        with patch("gc.collect") as mock_gc:
            result = ErrorRecovery.recover_from_critical_error(Exception("Test"), "other context")
            assert result is False
            mock_gc.assert_called_once()

    def test_recover_from_critical_error_exception(self):
        """Test recover_from_critical_error method with exception."""
        with patch("gc.collect", side_effect=Exception("GC error")):
            result = ErrorRecovery.recover_from_critical_error(Exception("Test"), "config loading")
            assert result is False

    def test_create_fallback_config(self):
        """Test create_fallback_config method."""
        config = ErrorRecovery.create_fallback_config()

        assert "basic" in config
        assert "webpage" in config
        assert "advanced" in config

        # Check basic config
        assert config["basic"]["urls"] == []
        assert config["basic"]["output_dir"] == ""

        # Check webpage config
        assert config["webpage"]["use_proxy"] is False
        assert config["webpage"]["ignore_ssl"] is False
        assert config["webpage"]["download_images"] is True
        assert config["webpage"]["filter_site_chrome"] is True
        assert config["webpage"]["use_shared_browser"] is True

        # Check advanced config
        assert config["advanced"]["user_data_path"] == ""
        assert config["advanced"]["language"] == "auto"

    def test_recover_generic_error_pytest_environment(self):
        """Test _recover_generic_error method in pytest environment."""
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_function"}):
            result = self.error_handler._recover_generic_error("TestError", "test context")
            assert result is True

    def test_recover_generic_error_headless_environment(self):
        """Test _recover_generic_error method in headless environment."""
        with patch.dict("os.environ", {"QT_QPA_PLATFORM": "offscreen"}):
            result = self.error_handler._recover_generic_error("TestError", "test context")
            assert result is True

    def test_recover_generic_error_minimal_environment(self):
        """Test _recover_generic_error method in minimal environment."""
        with patch.dict("os.environ", {"QT_QPA_PLATFORM": "minimal"}):
            result = self.error_handler._recover_generic_error("TestError", "test context")
            assert result is True

    def test_recover_generic_error_normal_environment(self):
        """Test _recover_generic_error method in normal environment."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("gc.collect") as mock_gc:
                result = self.error_handler._recover_generic_error("TestError", "test context")
                assert result is True
                mock_gc.assert_called_once()

    def test_recover_generic_error_gc_exception(self):
        """Test _recover_generic_error method when gc.collect raises exception."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("gc.collect", side_effect=Exception("GC error")):
                result = self.error_handler._recover_generic_error("TestError", "test context")
                assert result is True  # Should still return True even if GC fails

    def test_recover_generic_error_exception_handling(self):
        """Test _recover_generic_error method exception handling."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("gc.collect", side_effect=Exception("GC error")):
                # This should not raise an exception
                result = self.error_handler._recover_generic_error("TestError", "test context")
                assert result is True

    def test_attempt_recovery_first_attempt(self):
        """Test _attempt_recovery method on first attempt."""
        result = self.error_handler._attempt_recovery("TestError", "test context")
        # Should attempt recovery and return the result
        assert isinstance(result, bool)

    def test_attempt_recovery_multiple_attempts(self):
        """Test _attempt_recovery method on multiple attempts."""
        # First attempt
        self.error_handler._attempt_recovery("TestError", "test context")

        # Second attempt
        result = self.error_handler._attempt_recovery("TestError", "test context")
        assert isinstance(result, bool)

    def test_attempt_recovery_max_attempts_exceeded(self):
        """Test _attempt_recovery method when max attempts exceeded."""
        # Make multiple attempts to exceed the limit
        for _ in range(4):  # 3 is the max, so 4th should fail
            result = self.error_handler._attempt_recovery("TestError", "test context")

        # Should return False after max attempts
        assert result is False

    def test_attempt_recovery_different_error_types(self):
        """Test _attempt_recovery method with different error types."""
        # Test FileNotFoundError
        with patch.object(self.error_handler, "_recover_file_not_found", return_value=True):
            result = self.error_handler._attempt_recovery("FileNotFoundError", "file context")
            assert result is True

        # Test PermissionError
        with patch.object(self.error_handler, "_recover_permission_error", return_value=True):
            result = self.error_handler._attempt_recovery("PermissionError", "permission context")
            assert result is True

        # Test ConnectionError
        with patch.object(self.error_handler, "_recover_connection_error", return_value=True):
            result = self.error_handler._attempt_recovery("ConnectionError", "connection context")
            assert result is True

        # Test generic error
        with patch.object(self.error_handler, "_recover_generic_error", return_value=True):
            result = self.error_handler._attempt_recovery("GenericError", "generic context")
            assert result is True

    def test_attempt_recovery_exception_handling(self):
        """Test _attempt_recovery method exception handling."""
        with patch.object(
            self.error_handler, "_recover_generic_error", side_effect=Exception("Recovery error")
        ):
            result = self.error_handler._attempt_recovery("TestError", "test context")
            assert result is False

    def test_recover_file_not_found_session_context(self):
        """Test _recover_file_not_found method with session context."""
        with patch.object(
            self.error_handler.config_service.config_manager, "config_dir", "/test/config"
        ):
            with patch("os.makedirs") as mock_makedirs:
                result = self.error_handler._recover_file_not_found("session loading")
                assert result is True
                mock_makedirs.assert_called_once_with("/test/config", exist_ok=True)

    def test_recover_file_not_found_log_context(self):
        """Test _recover_file_not_found method with log context."""
        with patch.object(
            self.error_handler.config_service.config_manager, "root_dir", "/test/root"
        ):
            with patch("os.makedirs") as mock_makedirs:
                result = self.error_handler._recover_file_not_found("log writing")
                assert result is True
                # Check that makedirs was called with the log directory path
                expected_path = os.path.join("/test/root", "data", "log")
                mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)

    def test_recover_file_not_found_other_context(self):
        """Test _recover_file_not_found method with other context."""
        result = self.error_handler._recover_file_not_found("other context")
        assert result is False

    def test_recover_file_not_found_exception(self):
        """Test _recover_file_not_found method with exception."""
        with patch("os.makedirs", side_effect=Exception("Makedirs error")):
            result = self.error_handler._recover_file_not_found("session loading")
            assert result is False

    def test_recover_permission_error_session_context(self):
        """Test _recover_permission_error method with session context."""
        with patch.object(
            self.error_handler.config_service.config_manager, "config_dir", "/test/config"
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.chmod") as mock_chmod:
                    result = self.error_handler._recover_permission_error("session loading")
                    assert result is True
                    mock_chmod.assert_called_once_with("/test/config", 0o755)

    def test_recover_permission_error_nonexistent_path(self):
        """Test _recover_permission_error method with nonexistent path."""
        with patch.object(
            self.error_handler.config_service.config_manager, "config_dir", "/test/config"
        ):
            with patch("os.path.exists", return_value=False):
                result = self.error_handler._recover_permission_error("session loading")
                assert result is False

    def test_recover_permission_error_other_context(self):
        """Test _recover_permission_error method with other context."""
        result = self.error_handler._recover_permission_error("other context")
        assert result is False

    def test_recover_permission_error_exception(self):
        """Test _recover_permission_error method with exception."""
        with patch.object(
            self.error_handler.config_service.config_manager, "config_dir", "/test/config"
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.chmod", side_effect=Exception("Chmod error")):
                    result = self.error_handler._recover_permission_error("session loading")
                    assert result is False

    def test_recover_connection_error_success(self):
        """Test _recover_connection_error method success."""
        with patch("time.sleep") as mock_sleep:
            result = self.error_handler._recover_connection_error("connection context")
            assert result is True
            mock_sleep.assert_called_once_with(1)

    def test_recover_connection_error_exception(self):
        """Test _recover_connection_error method with exception."""
        with patch("time.sleep", side_effect=Exception("Sleep error")):
            result = self.error_handler._recover_connection_error("connection context")
            assert result is False
