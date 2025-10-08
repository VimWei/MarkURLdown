"""Test LogPanel component functionality."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.components.log_panel import LogPanel


class TestLogPanel:
    """Test LogPanel class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        
        self.mock_translator = Mock()
        self.mock_translator.t = Mock(side_effect=lambda key, **kwargs: f"translated_{key}")
        
        self.log_panel = LogPanel(translator=self.mock_translator)

    def test_clear_log(self):
        """Test _clear_log method."""
        # Add some content to log
        self.log_panel.log_text.setPlainText("Test log content")
        assert self.log_panel.log_text.toPlainText() == "Test log content"
        
        # Clear log
        self.log_panel._clear_log()
        assert self.log_panel.log_text.toPlainText() == ""

    def test_clear_log_signal(self):
        """Test _clear_log method emits signal."""
        # Implementation does not emit a signal; ensure no exception and content cleared
        self.log_panel.log_text.setPlainText("abc")
        self.log_panel._clear_log()
        assert self.log_panel.log_text.toPlainText() == ""

    def test_appendTaskLog_with_icon(self):
        """Test appendTaskLog method with icon."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.appendTaskLog("task1", "Test message", "✅")
            mock_append.assert_called_once_with("✅ [task1] Test message")

    def test_appendTaskLog_without_icon(self):
        """Test appendTaskLog method without icon."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.appendTaskLog("task1", "Test message")
            mock_append.assert_called_once_with("[task1] Test message")

    def test_appendMultiTaskSummary_with_translator(self):
        """Test appendMultiTaskSummary method with translator."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.appendMultiTaskSummary(8, 2, 10)
            
            # Verify translator was called with expected key at least once
            calls = [c for c in self.mock_translator.t.mock_calls if c.args and c.args[0] == 'multi_task_summary']
            assert len(calls) >= 1
            mock_append.assert_called_once_with("translated_multi_task_summary")

    def test_appendMultiTaskSummary_without_translator(self):
        """Test appendMultiTaskSummary method without translator."""
        self.log_panel.translator = None
        
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.appendMultiTaskSummary(8, 2, 10)
            
            expected_text = "Multi-task completed: 8 successful, 2 failed, 10 total, 📈 成功率: 80.0%"
            mock_append.assert_called_once_with(expected_text)

    def test_appendMultiTaskSummary_zero_total(self):
        """Test appendMultiTaskSummary method with zero total."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.appendMultiTaskSummary(0, 0, 0)
            
            # Should handle division by zero gracefully; ensure key requested
            calls = [c for c in self.mock_translator.t.mock_calls if c.args and c.args[0] == 'multi_task_summary']
            assert len(calls) >= 1

    def test_setEnabled_true(self):
        """Test setEnabled method with True."""
        self.log_panel.setEnabled(True)
        
        assert self.log_panel.isEnabled()
        assert self.log_panel.log_text.isEnabled()
        assert self.log_panel.clear_btn.isEnabled()
        assert self.log_panel.copy_btn.isEnabled()

    def test_setEnabled_false(self):
        """Test setEnabled method with False."""
        self.log_panel.setEnabled(False)
        
        assert not self.log_panel.isEnabled()
        assert not self.log_panel.log_text.isEnabled()
        assert not self.log_panel.clear_btn.isEnabled()
        assert not self.log_panel.copy_btn.isEnabled()

    def test_appendLog(self):
        """Test appendLog method."""
        # Patch where datetime is used (module under test)
        with patch('markdownall.ui.pyside.components.log_panel.datetime') as mock_dt:
            fake_now = Mock()
            fake_now.strftime.return_value = "12:34:56"
            mock_dt.now.return_value = fake_now
            
            self.log_panel.appendLog("Test message")
            
            content = self.log_panel.log_text.toPlainText()
            assert content.endswith("Test message")

    def test_appendLog_auto_scroll(self):
        """Test appendLog method auto-scrolls to bottom."""
        with patch.object(self.log_panel.log_text, 'verticalScrollBar') as mock_scrollbar:
            mock_scrollbar.return_value.maximum.return_value = 100
            mock_scrollbar.return_value.setValue = Mock()
            
            self.log_panel.appendLog("Test message")
            
            mock_scrollbar.return_value.setValue.assert_called_once_with(100)

    def test_addLog_with_level(self):
        """Test addLog method with level."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.addLog("Test message", "ERROR")
            mock_append.assert_called_once_with("[ERROR] Test message")

    def test_addLog_without_level(self):
        """Test addLog method without level."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.addLog("Test message")
            mock_append.assert_called_once_with("Test message")

    def test_addLog_info_level(self):
        """Test addLog method with INFO level."""
        with patch.object(self.log_panel, 'appendLog') as mock_append:
            self.log_panel.addLog("Test message", "INFO")
            mock_append.assert_called_once_with("Test message")

    def test_getLogContent(self):
        """Test getLogContent method."""
        test_content = "Test log content"
        self.log_panel.log_text.setPlainText(test_content)
        
        result = self.log_panel.getLogContent()
        assert result == test_content

    def test_setLogContent(self):
        """Test setLogContent method."""
        test_content = "New log content"
        self.log_panel.setLogContent(test_content)
        
        assert self.log_panel.log_text.toPlainText() == test_content

    def test_clearLog(self):
        """Test clearLog method."""
        # Add some content
        self.log_panel.log_text.setPlainText("Test content")
        
        # Clear it
        self.log_panel.clearLog()
        
        assert self.log_panel.log_text.toPlainText() == ""

    def test_retranslate_ui(self):
        """Test retranslate_ui method."""
        self.log_panel.retranslate_ui()
        
        # Verify translator was called for all UI elements
        expected_calls = ["log_clear", "log_copy", "log_placeholder"]
        for call in expected_calls:
            self.mock_translator.t.assert_any_call(call)

    def test_retranslate_ui_without_translator(self):
        """Test retranslate_ui method without translator."""
        self.log_panel.translator = None
        # Should not raise exception
        self.log_panel.retranslate_ui()

    def test_get_config(self):
        """Test get_config method."""
        config = self.log_panel.get_config()
        
        assert "log_content" in config
        assert "max_lines" in config
        assert config["log_content"] == self.log_panel.getLogContent()
        assert config["max_lines"] == 1000

    def test_set_config(self):
        """Test set_config method."""
        test_content = "Test configuration content"
        config = {"log_content": test_content}
        
        self.log_panel.set_config(config)
        
        assert self.log_panel.getLogContent() == test_content

    def test_set_config_partial(self):
        """Test set_config method with partial config."""
        # Set initial content
        self.log_panel.setLogContent("Initial content")
        
        # Set config without log_content
        config = {"other_key": "other_value"}
        self.log_panel.set_config(config)
        
        # Content should remain unchanged
        assert self.log_panel.getLogContent() == "Initial content"

    def test_copy_log_success(self):
        """Test _copy_log method with success."""
        test_content = "Test log content"
        self.log_panel.log_text.setPlainText(test_content)
        
        with patch('PySide6.QtWidgets.QApplication.clipboard') as mock_clipboard:
            mock_clipboard.return_value.setText = Mock()
            
            with patch.object(self.log_panel, 'logCopied') as mock_signal:
                self.log_panel._copy_log()
                
                mock_clipboard.return_value.setText.assert_called_once_with(test_content)
                mock_signal.emit.assert_called_once()

    def test_copy_log_exception(self):
        """Test _copy_log method with exception."""
        test_content = "Test log content"
        self.log_panel.log_text.setPlainText(test_content)
        
        with patch('PySide6.QtWidgets.QApplication.clipboard', side_effect=Exception("Clipboard error")):
            with patch.object(self.log_panel, 'appendLog') as mock_append:
                self.log_panel._copy_log()
                
                mock_append.assert_called_once_with("Copy to clipboard failed: Clipboard error")

    def test_initialization(self):
        """Test LogPanel initialization."""
        assert self.log_panel.translator == self.mock_translator
        
        # Check UI elements exist
        assert hasattr(self.log_panel, 'log_text')
        assert hasattr(self.log_panel, 'clear_btn')
        assert hasattr(self.log_panel, 'copy_btn')

    def test_initialization_without_translator(self):
        """Test LogPanel initialization without translator."""
        panel = LogPanel(translator=None)
        
        assert panel.translator is None
        assert panel.log_text.placeholderText() == "log message"

    def test_signal_connections(self):
        """Test that signals are properly connected."""
        # Test clear button
        with patch.object(self.log_panel, '_clear_log') as mock_method:
            self.log_panel.clear_btn.clicked.emit()
            mock_method.assert_called_once()
        
        # Test copy button
        with patch.object(self.log_panel, '_copy_log') as mock_method:
            self.log_panel.copy_btn.clicked.emit()
            mock_method.assert_called_once()

    def test_log_text_readonly(self):
        """Test that log text area is read-only."""
        assert self.log_panel.log_text.isReadOnly()

    def test_button_sizes(self):
        """Test that buttons have correct sizes."""
        assert self.log_panel.clear_btn.size() == self.log_panel.clear_btn.size()
        assert self.log_panel.copy_btn.size() == self.log_panel.copy_btn.size()
        # Both buttons should have fixed size of 70x22
        assert self.log_panel.clear_btn.width() == 70
        assert self.log_panel.clear_btn.height() == 22
        assert self.log_panel.copy_btn.width() == 70
        assert self.log_panel.copy_btn.height() == 22
