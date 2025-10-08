"""Test CommandPanel component functionality."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.components.command_panel import CommandPanel


class TestCommandPanel:
    """Test CommandPanel class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        
        self.mock_translator = Mock()
        self.mock_translator.t = Mock(side_effect=lambda key, **kwargs: f"translated_{key}")
        
        self.command_panel = CommandPanel(translator=self.mock_translator)

    def test_on_convert_clicked_not_converting(self):
        """Test _on_convert_clicked method when not converting."""
        self.command_panel._is_converting = False
        
        with patch.object(self.command_panel, 'convertRequested') as mock_signal:
            self.command_panel._on_convert_clicked()
            mock_signal.emit.assert_called_once()

    def test_on_convert_clicked_converting(self):
        """Test _on_convert_clicked method when converting."""
        self.command_panel._is_converting = True
        
        with patch.object(self.command_panel, 'stopRequested') as mock_signal:
            self.command_panel._on_convert_clicked()
            mock_signal.emit.assert_called_once()

    def test_setConvertButtonText(self):
        """Test setConvertButtonText method."""
        test_text = "Test Button Text"
        self.command_panel.setConvertButtonText(test_text)
        assert self.command_panel.btn_convert.text() == test_text

    def test_setEnabled_true(self):
        """Test setEnabled method with True."""
        self.command_panel.setEnabled(True)
        
        assert self.command_panel.isEnabled()
        assert self.command_panel.btn_restore.isEnabled()
        assert self.command_panel.btn_import.isEnabled()
        assert self.command_panel.btn_export.isEnabled()
        assert self.command_panel.btn_convert.isEnabled()

    def test_setEnabled_false(self):
        """Test setEnabled method with False."""
        self.command_panel.setEnabled(False)
        
        assert not self.command_panel.isEnabled()
        assert not self.command_panel.btn_restore.isEnabled()
        assert not self.command_panel.btn_import.isEnabled()
        assert not self.command_panel.btn_export.isEnabled()
        assert not self.command_panel.btn_convert.isEnabled()

    def test_setProgress(self):
        """Test setProgress method."""
        # Test normal value
        self.command_panel.setProgress(50)
        assert self.command_panel.progress.value() == 50
        
        # Test value clamping
        self.command_panel.setProgress(150)
        assert self.command_panel.progress.value() == 100
        
        self.command_panel.setProgress(-10)
        assert self.command_panel.progress.value() == 0

    def test_setProgress_with_format_change(self):
        """Test setProgress method with format change."""
        # Set initial format to ready text
        self.command_panel.progress.setFormat(self.command_panel._ready_text)
        
        # Set progress should change format to percentage
        self.command_panel.setProgress(50)
        assert self.command_panel.progress.format() == "%p%"

    def test_setProgress_with_percentage_format(self):
        """Test setProgress method with percentage format."""
        # Set initial format to percentage
        self.command_panel.progress.setFormat("%p%")
        
        # Set progress should keep percentage format
        self.command_panel.setProgress(75)
        assert self.command_panel.progress.format() == "%p%"

    def test_set_progress_with_text(self):
        """Test set_progress method with text."""
        with patch.object(self.command_panel, 'setProgress') as mock_set_progress:
            with patch.object(self.command_panel, 'setProgressText') as mock_set_text:
                self.command_panel.set_progress(60, "Processing...")
                
                mock_set_progress.assert_called_once_with(60)
                mock_set_text.assert_called_once_with("Processing...")

    def test_set_progress_without_text(self):
        """Test set_progress method without text."""
        with patch.object(self.command_panel, 'setProgress') as mock_set_progress:
            with patch.object(self.command_panel, 'setProgressText') as mock_set_text:
                self.command_panel.set_progress(60)
                
                mock_set_progress.assert_called_once_with(60)
                mock_set_text.assert_not_called()

    def test_setProgressText(self):
        """Test setProgressText method."""
        test_text = "Custom progress text"
        self.command_panel.setProgressText(test_text)
        assert self.command_panel.progress.format() == test_text

    def test_setConvertingState_true(self):
        """Test setConvertingState method with True."""
        self.command_panel.setConvertingState(True)
        
        assert self.command_panel._is_converting is True
        assert self.command_panel.btn_convert.text() == "translated_command_stop"
        assert self.command_panel.btn_convert.property("mode") == "stop"

    def test_setConvertingState_false(self):
        """Test setConvertingState method with False."""
        self.command_panel.setConvertingState(False)
        
        assert self.command_panel._is_converting is False
        assert self.command_panel.btn_convert.text() == "translated_command_convert"
        assert self.command_panel.btn_convert.property("mode") == "convert"

    def test_setConvertingState_without_translator(self):
        """Test setConvertingState method without translator."""
        self.command_panel.translator = None
        self.command_panel.setConvertingState(True)
        
        assert self.command_panel._is_converting is True
        assert self.command_panel.btn_convert.text() == "Stop"

    def test_setConvertingState_style_refresh(self):
        """Test setConvertingState method with style refresh."""
        # Test that setConvertingState changes the button state
        self.command_panel.setConvertingState(True)
        assert self.command_panel._is_converting == True
        
        self.command_panel.setConvertingState(False)
        assert self.command_panel._is_converting == False

    def test_retranslate_ui(self):
        """Test retranslate_ui method."""
        self.command_panel.retranslate_ui()
        
        # Verify that retranslate_ui was called (translator calls are internal)
        assert self.command_panel.btn_convert.text() == "translated_command_convert"

    def test_retranslate_ui_without_translator(self):
        """Test retranslate_ui method without translator."""
        self.command_panel.translator = None
        # Should not raise exception
        self.command_panel.retranslate_ui()

    def test_retranslate_ui_converting_state(self):
        """Test retranslate_ui method when converting."""
        self.command_panel._is_converting = True
        self.command_panel.retranslate_ui()
        
        # Should call command_stop instead of command_convert
        # Verify the button text was set (translator calls are internal)
        assert self.command_panel.btn_convert.text() == "translated_command_stop"

    def test_retranslate_ui_progress_format_update(self):
        """Test retranslate_ui method updates progress format when idle."""
        # Set progress to 0 and not converting
        self.command_panel.progress.setValue(0)
        self.command_panel._is_converting = False
        
        self.command_panel.retranslate_ui()
        
        # Should update progress format to new ready text
        assert self.command_panel.progress.format() == "translated_progress_ready"

    def test_get_config(self):
        """Test get_config method."""
        config = self.command_panel.get_config()
        
        assert "convert_button_text" in config
        assert config["convert_button_text"] == self.command_panel.btn_convert.text()

    def test_initialization(self):
        """Test CommandPanel initialization."""
        assert self.command_panel.translator == self.mock_translator
        assert self.command_panel._is_converting is False
        assert self.command_panel._ready_text == "translated_progress_ready"
        
        # Check UI elements exist
        assert hasattr(self.command_panel, 'btn_restore')
        assert hasattr(self.command_panel, 'btn_import')
        assert hasattr(self.command_panel, 'btn_export')
        assert hasattr(self.command_panel, 'btn_convert')
        assert hasattr(self.command_panel, 'progress')

    def test_initialization_without_translator(self):
        """Test CommandPanel initialization without translator."""
        panel = CommandPanel(translator=None)
        
        assert panel.translator is None
        assert panel._ready_text == "Ready"

    def test_signal_connections(self):
        """Test that signals are properly connected."""
        # Test convert button (calls _on_convert_clicked)
        with patch.object(self.command_panel, '_on_convert_clicked') as mock_method:
            self.command_panel.btn_convert.clicked.emit()
            mock_method.assert_called_once()
        
        # Test that buttons exist and are clickable
        assert self.command_panel.btn_convert is not None
        assert self.command_panel.btn_import is not None
        assert self.command_panel.btn_export is not None
        assert self.command_panel.btn_restore is not None

    def test_fixed_height(self):
        """Test that CommandPanel has fixed height."""
        assert self.command_panel.height() == 120
        from PySide6.QtWidgets import QSizePolicy
        assert self.command_panel.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed
