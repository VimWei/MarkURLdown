"""Test ConvertService LoggerAdapter and TaskAwareLogger functionality."""

import threading
from unittest.mock import MagicMock, Mock, patch

import pytest

from markdownall.app_types import ProgressEvent
from markdownall.services.convert_service import ConvertService, LoggerAdapter


class TestLoggerAdapter:
    """Test LoggerAdapter class."""

    def setup_method(self):
        """Setup test environment."""
        self.mock_ui = Mock()
        self.mock_signals = Mock()
        self.logger = LoggerAdapter(self.mock_ui, self.mock_signals)

    def test_info(self):
        """Test info method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.info("Test info message")
            mock_emit.assert_called_once_with(kind="status", text="Test info message")

    def test_success(self):
        """Test success method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.success("Test success message")
            mock_emit.assert_called_once_with(kind="detail", text="Test success message")

    def test_warning(self):
        """Test warning method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.warning("Test warning message")
            mock_emit.assert_called_once_with(kind="detail", text="⚠️ Test warning message")

    def test_error(self):
        """Test error method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.error("Test error message")
            mock_emit.assert_called_once_with(kind="error", text="❌ Test error message")

    def test_images_progress(self):
        """Test images_progress method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.images_progress(5, 1, 3)
            mock_emit.assert_called_once_with(
                kind="status",
                key="images_dl_progress",
                data={"total": 5, "task_idx": 1, "task_total": 3},
                text="[图片] 发现 5 张图片，开始下载...",
            )

    def test_images_progress_with_exception(self):
        """Test images_progress method with exception."""
        with patch.object(self.logger, "_emit_progress", side_effect=Exception("Test error")):
            with patch("builtins.print") as mock_print:
                self.logger.images_progress(5)
                mock_print.assert_called_once_with("[图片] 发现 5 张图片，开始下载...")

    def test_images_done(self):
        """Test images_done method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.images_done(5, 1, 3)
            mock_emit.assert_called_once_with(
                kind="status",
                key="images_dl_done",
                data={"total": 5, "task_idx": 1, "task_total": 3},
                text="[图片] 下载完成: 5 张图片",
            )

    def test_images_done_with_exception(self):
        """Test images_done method with exception."""
        with patch.object(self.logger, "_emit_progress", side_effect=Exception("Test error")):
            with patch("builtins.print") as mock_print:
                self.logger.images_done(5)
                mock_print.assert_called_once_with("[图片] 下载完成: 5 张图片")

    def test_debug(self):
        """Test debug method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.debug("Test debug message")
            mock_emit.assert_called_once_with(kind="status", text="Test debug message")

    def test_fetch_start_no_retry(self):
        """Test fetch_start method without retry."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_start("TestStrategy")
            mock_emit.assert_called_once_with(
                kind="status", key="phase_fetch_start", text="[抓取] TestStrategy..."
            )

    def test_fetch_start_with_retry(self):
        """Test fetch_start method with retry."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_start("TestStrategy", retry=2, max_retries=5)
            mock_emit.assert_called_once_with(
                kind="status", key="phase_fetch_start", text="[抓取] TestStrategy重试 2/4..."
            )

    def test_fetch_success(self):
        """Test fetch_success method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_success(1000)
            mock_emit.assert_called_once_with(
                kind="status", text="[抓取] 成功获取内容 (内容长度: 1000 字符)"
            )

    def test_fetch_success_no_length(self):
        """Test fetch_success method without content length."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_success()
            mock_emit.assert_called_once_with(kind="status", text="[抓取] 成功获取内容")

    def test_fetch_failed(self):
        """Test fetch_failed method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_failed("TestStrategy", "Connection error")
            mock_emit.assert_called_once_with(
                kind="detail", text="[抓取] TestStrategy策略失败: Connection error"
            )

    def test_fetch_retry(self):
        """Test fetch_retry method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.fetch_retry("TestStrategy", 2, 5)
            mock_emit.assert_called_once_with(kind="status", text="[抓取] TestStrategy重试 2/4...")

    def test_parse_start(self):
        """Test parse_start method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.parse_start()
            mock_emit.assert_called_once_with(
                kind="status", key="phase_parse_start", text="[解析] 提取标题和正文..."
            )

    def test_parse_title(self):
        """Test parse_title method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.parse_title("Test Title")
            mock_emit.assert_called_once_with(kind="status", text="[解析] 标题: Test Title")

    def test_parse_content_short(self):
        """Test parse_content_short method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.parse_content_short(100, 200)
            mock_emit.assert_called_once_with(
                kind="detail", text="[解析] 内容太短 (100 字符)，尝试下一个策略"
            )

    def test_parse_success(self):
        """Test parse_success method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.parse_success(1500)
            mock_emit.assert_called_once_with(
                kind="status", text="[解析] 解析成功，内容长度: 1500 字符"
            )

    def test_clean_start(self):
        """Test clean_start method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.clean_start()
            mock_emit.assert_called_once_with(
                kind="status", key="phase_clean_start", text="[清理] 移除广告和无关内容..."
            )

    def test_clean_success(self):
        """Test clean_success method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.clean_success()
            mock_emit.assert_called_once_with(kind="status", text="[清理] 内容清理完成")

    def test_convert_start(self):
        """Test convert_start method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.convert_start()
            mock_emit.assert_called_once_with(
                kind="status", key="phase_convert_start", text="[转换] 转换为Markdown..."
            )

    def test_convert_success(self):
        """Test convert_success method (should do nothing)."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.convert_success()
            mock_emit.assert_not_called()

    def test_url_success(self):
        """Test url_success method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.url_success("Test Title")
            mock_emit.assert_called_once_with(kind="detail", text="✅ URL处理成功: Test Title")

    def test_url_failed(self):
        """Test url_failed method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.url_failed("https://example.com", "Network error")
            mock_emit.assert_called_once_with(
                kind="error", text="❌ URL处理失败: https://example.com - Network error"
            )

    def test_batch_start(self):
        """Test batch_start method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.batch_start(10)
            mock_emit.assert_called_once_with(
                kind="status",
                key="batch_start",
                data={"total": 10},
                text="🚀 开始批量处理 10 个URL...",
            )

    def test_batch_summary(self):
        """Test batch_summary method (should do nothing)."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.batch_summary(8, 2, 10)
            mock_emit.assert_not_called()

    def test_task_status(self):
        """Test task_status method."""
        with patch.object(self.logger, "_emit_progress") as mock_emit:
            self.logger.task_status(1, 5, "https://example.com")
            mock_emit.assert_called_once_with(
                kind="status",
                data={"url": "https://example.com", "idx": 1, "total": 5},
                text="Processing: https://example.com",
            )

    def test_task_status_with_exception(self):
        """Test task_status method with exception."""
        with patch.object(self.logger, "_emit_progress", side_effect=Exception("Test error")):
            with patch("builtins.print") as mock_print:
                self.logger.task_status(1, 5, "https://example.com")
                mock_print.assert_called_once_with("Processing: https://example.com")

    def test_emit_progress_with_signals(self):
        """Test _emit_progress method with signals."""
        mock_signals = Mock()
        mock_signals.progress_event = Mock()
        logger = LoggerAdapter(None, mock_signals)

        with patch("markdownall.app_types.ProgressEvent") as mock_event_class:
            mock_event = Mock()
            mock_event_class.return_value = mock_event

            logger._emit_progress(kind="test", text="test message")

            mock_event_class.assert_called_once_with(
                kind="test", key=None, text="test message", data=None
            )
            mock_signals.progress_event.emit.assert_called_once_with(mock_event)

    def test_emit_progress_with_signals_exception(self):
        """Test _emit_progress method with signals exception."""
        mock_signals = Mock()
        mock_signals.progress_event = Mock(side_effect=Exception("Signal error"))
        logger = LoggerAdapter(None, mock_signals)

        with patch.object(logger, "_call") as mock_call:
            logger._emit_progress(kind="test", text="test message")
            mock_call.assert_called_once_with("test", "test message")

    def test_emit_progress_no_signals(self):
        """Test _emit_progress method without signals."""
        logger = LoggerAdapter(None, None)

        with patch.object(logger, "_call") as mock_call:
            logger._emit_progress(kind="test", text="test message")
            mock_call.assert_called_once_with("test", "test message")

    def test_call_main_thread(self):
        """Test _call method in main thread."""
        mock_ui = Mock()
        mock_ui.log_info = Mock()
        logger = LoggerAdapter(mock_ui, None)

        with patch("threading.current_thread") as mock_thread:
            mock_thread.return_value.name = "MainThread"

            logger._call("status", "test message")
            mock_ui.log_info.assert_called_once_with("test message")

    def test_call_background_thread(self):
        """Test _call method in background thread."""
        mock_ui = Mock()
        logger = LoggerAdapter(mock_ui, None)

        with patch("threading.current_thread") as mock_thread:
            mock_thread.return_value.name = "BackgroundThread"

            with patch("builtins.print") as mock_print:
                logger._call("status", "test message")
                mock_print.assert_called_once_with("test message")

    def test_call_ui_method_mapping(self):
        """Test _call method UI method mapping."""
        mock_ui = Mock()
        mock_ui.log_success = Mock()
        mock_ui.log_error = Mock()
        mock_ui.log_info = Mock()
        logger = LoggerAdapter(mock_ui, None)

        with patch("threading.current_thread") as mock_thread:
            mock_thread.return_value.name = "MainThread"

            # Test progress_done -> log_success
            logger._call("progress_done", "success message")
            mock_ui.log_success.assert_called_once_with("success message")

            # Test error -> log_error
            logger._call("error", "error message")
            mock_ui.log_error.assert_called_once_with("error message")

            # Test default -> log_info
            logger._call("status", "info message")
            mock_ui.log_info.assert_called_once_with("info message")

    def test_call_exception_handling(self):
        """Test _call method exception handling."""
        mock_ui = Mock()
        mock_ui.log_info = Mock(side_effect=Exception("UI error"))
        logger = LoggerAdapter(mock_ui, None)

        with patch("threading.current_thread") as mock_thread:
            mock_thread.return_value.name = "MainThread"

            with patch("builtins.print") as mock_print:
                logger._call("status", "test message")
                mock_print.assert_called_once_with("test message")


class TestTaskAwareLogger:
    """Test TaskAwareLogger class (nested in ConvertService._worker)."""

    def setup_method(self):
        """Setup test environment."""
        self.mock_base_logger = Mock()

        # Create a local test-double that mirrors the behavior of the inner _TaskAwareLogger
        class TaskAwareLike:
            def __init__(self, base_logger, task_idx: int, task_total: int):
                self._base = base_logger
                self._task_idx = task_idx
                self._task_total = task_total

            # Basic forwards
            def info(self, msg: str) -> None:
                self._base.info(msg)

            def success(self, msg: str) -> None:
                self._base.success(msg)

            def warning(self, msg: str) -> None:
                self._base.warning(msg)

            def error(self, msg: str) -> None:
                self._base.error(msg)

            def task_status(self, t_idx: int, t_total: int, url: str) -> None:
                self._base.task_status(t_idx, t_total, url)

            # Inject task context defaults when not provided
            def images_progress(
                self, total_imgs: int, task_idx: int | None = None, task_total: int | None = None
            ) -> None:
                self._base.images_progress(
                    total_imgs,
                    task_idx=self._task_idx if task_idx is None else task_idx,
                    task_total=self._task_total if task_total is None else task_total,
                )

            def images_done(
                self, total_imgs: int, task_idx: int | None = None, task_total: int | None = None
            ) -> None:
                self._base.images_done(
                    total_imgs,
                    task_idx=self._task_idx if task_idx is None else task_idx,
                    task_total=self._task_total if task_total is None else task_total,
                )

            def debug(self, msg: str) -> None:
                self._base.debug(msg)

            # Stage logs
            def fetch_start(self, strategy_name: str, retry: int = 0, max_retries: int = 0) -> None:
                self._base.fetch_start(strategy_name, retry, max_retries)

            def fetch_success(self, content_length: int = 0) -> None:
                self._base.fetch_success(content_length)

            def fetch_failed(self, strategy_name: str, error: str) -> None:
                self._base.fetch_failed(strategy_name, error)

            def fetch_retry(self, strategy_name: str, retry: int, max_retries: int) -> None:
                self._base.fetch_retry(strategy_name, retry, max_retries)

            def parse_start(self) -> None:
                self._base.parse_start()

            def parse_title(self, title: str) -> None:
                self._base.parse_title(title)

            def parse_content_short(self, length: int, min_length: int = 200) -> None:
                self._base.parse_content_short(length, min_length)

            def parse_success(self, content_length: int) -> None:
                self._base.parse_success(content_length)

            def clean_start(self) -> None:
                self._base.clean_start()

            def clean_success(self) -> None:
                self._base.clean_success()

            def convert_start(self) -> None:
                self._base.convert_start()

            def convert_success(self) -> None:
                self._base.convert_success()

            def url_success(self, title: str) -> None:
                self._base.url_success(title)

            def url_failed(self, url: str, error: str) -> None:
                self._base.url_failed(url, error)

            def batch_start(self, total: int) -> None:
                self._base.batch_start(total)

            def batch_summary(self, success: int, failed: int, total: int) -> None:
                self._base.batch_summary(success, failed, total)

        self.task_logger = TaskAwareLike(self.mock_base_logger, 2, 5)

    def test_info(self):
        """Test info method."""
        self.task_logger.info("Test message")
        self.mock_base_logger.info.assert_called_once_with("Test message")

    def test_success(self):
        """Test success method."""
        self.task_logger.success("Test message")
        self.mock_base_logger.success.assert_called_once_with("Test message")

    def test_warning(self):
        """Test warning method."""
        self.task_logger.warning("Test message")
        self.mock_base_logger.warning.assert_called_once_with("Test message")

    def test_error(self):
        """Test error method."""
        self.task_logger.error("Test message")
        self.mock_base_logger.error.assert_called_once_with("Test message")

    def test_task_status(self):
        """Test task_status method."""
        self.task_logger.task_status(1, 3, "https://example.com")
        self.mock_base_logger.task_status.assert_called_once_with(1, 3, "https://example.com")

    def test_images_progress_with_task_context(self):
        """Test images_progress method with task context injection."""
        self.task_logger.images_progress(10)
        self.mock_base_logger.images_progress.assert_called_once_with(10, task_idx=2, task_total=5)

    def test_images_progress_with_explicit_params(self):
        """Test images_progress method with explicit parameters."""
        self.task_logger.images_progress(10, task_idx=1, task_total=3)
        self.mock_base_logger.images_progress.assert_called_once_with(10, task_idx=1, task_total=3)

    def test_images_done_with_task_context(self):
        """Test images_done method with task context injection."""
        self.task_logger.images_done(10)
        self.mock_base_logger.images_done.assert_called_once_with(10, task_idx=2, task_total=5)

    def test_images_done_with_explicit_params(self):
        """Test images_done method with explicit parameters."""
        self.task_logger.images_done(10, task_idx=1, task_total=3)
        self.mock_base_logger.images_done.assert_called_once_with(10, task_idx=1, task_total=3)

    def test_debug(self):
        """Test debug method."""
        self.task_logger.debug("Test message")
        self.mock_base_logger.debug.assert_called_once_with("Test message")

    def test_fetch_start(self):
        """Test fetch_start method."""
        self.task_logger.fetch_start("TestStrategy", 1, 3)
        self.mock_base_logger.fetch_start.assert_called_once_with("TestStrategy", 1, 3)

    def test_fetch_success(self):
        """Test fetch_success method."""
        self.task_logger.fetch_success(1000)
        self.mock_base_logger.fetch_success.assert_called_once_with(1000)

    def test_fetch_failed(self):
        """Test fetch_failed method."""
        self.task_logger.fetch_failed("TestStrategy", "Error")
        self.mock_base_logger.fetch_failed.assert_called_once_with("TestStrategy", "Error")

    def test_fetch_retry(self):
        """Test fetch_retry method."""
        self.task_logger.fetch_retry("TestStrategy", 1, 3)
        self.mock_base_logger.fetch_retry.assert_called_once_with("TestStrategy", 1, 3)

    def test_parse_start(self):
        """Test parse_start method."""
        self.task_logger.parse_start()
        self.mock_base_logger.parse_start.assert_called_once()

    def test_parse_title(self):
        """Test parse_title method."""
        self.task_logger.parse_title("Test Title")
        self.mock_base_logger.parse_title.assert_called_once_with("Test Title")

    def test_parse_content_short(self):
        """Test parse_content_short method."""
        self.task_logger.parse_content_short(100, 200)
        self.mock_base_logger.parse_content_short.assert_called_once_with(100, 200)

    def test_parse_success(self):
        """Test parse_success method."""
        self.task_logger.parse_success(1500)
        self.mock_base_logger.parse_success.assert_called_once_with(1500)

    def test_clean_start(self):
        """Test clean_start method."""
        self.task_logger.clean_start()
        self.mock_base_logger.clean_start.assert_called_once()

    def test_clean_success(self):
        """Test clean_success method."""
        self.task_logger.clean_success()
        self.mock_base_logger.clean_success.assert_called_once()

    def test_convert_start(self):
        """Test convert_start method."""
        self.task_logger.convert_start()
        self.mock_base_logger.convert_start.assert_called_once()

    def test_convert_success(self):
        """Test convert_success method."""
        self.task_logger.convert_success()
        self.mock_base_logger.convert_success.assert_called_once()

    def test_url_success(self):
        """Test url_success method."""
        self.task_logger.url_success("Test Title")
        self.mock_base_logger.url_success.assert_called_once_with("Test Title")

    def test_url_failed(self):
        """Test url_failed method."""
        self.task_logger.url_failed("https://example.com", "Error")
        self.mock_base_logger.url_failed.assert_called_once_with("https://example.com", "Error")

    def test_batch_start(self):
        """Test batch_start method."""
        self.task_logger.batch_start(10)
        self.mock_base_logger.batch_start.assert_called_once_with(10)

    def test_batch_summary(self):
        """Test batch_summary method."""
        self.task_logger.batch_summary(8, 2, 10)
        self.mock_base_logger.batch_summary.assert_called_once_with(8, 2, 10)
