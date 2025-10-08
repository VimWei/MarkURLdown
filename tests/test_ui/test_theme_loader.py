"""Test ThemeLoader functionality."""

import os
import tempfile
from unittest.mock import Mock, patch, mock_open

import pytest
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.styles.theme_loader import ThemeLoader


class TestThemeLoader:
    """Test ThemeLoader class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_init_default_theme(self):
        """Test ThemeLoader initialization with default theme."""
        loader = ThemeLoader()
        assert loader.theme_name == "default"
        assert loader.theme_dir.name == "themes"

    def test_init_custom_theme(self):
        """Test ThemeLoader initialization with custom theme."""
        loader = ThemeLoader("dark")
        assert loader.theme_name == "dark"
        assert loader.theme_dir.name == "themes"

    def test_load_theme_existing_file(self):
        """Test load_theme method with existing theme file."""
        loader = ThemeLoader("test_theme")
        test_content = "QWidget { background-color: red; }"
        
        # Patch Path.__truediv__ at class level to avoid attribute errors on WindowsPath instances
        with patch('pathlib.Path.__truediv__', return_value=Mock(exists=Mock(return_value=True))):
            with patch('builtins.open', mock_open(read_data=test_content)):
                content = loader.load_theme()
                assert content == test_content

    def test_load_theme_fallback_to_default(self):
        """Test load_theme method falls back to default theme."""
        loader = ThemeLoader("nonexistent_theme")
        test_content = "QWidget { background-color: blue; }"
        
        # Mock the theme file doesn't exist, but default does
        mock_theme_file = Mock()
        mock_theme_file.exists.return_value = False
        mock_default_file = Mock()
        mock_default_file.exists.return_value = True
        
        with patch('pathlib.Path.__truediv__', side_effect=[mock_theme_file, mock_default_file]):
            with patch('builtins.open', mock_open(read_data=test_content)):
                content = loader.load_theme()
                assert content == test_content

    def test_load_theme_no_files_exist(self):
        """Test load_theme method when no theme files exist."""
        loader = ThemeLoader("nonexistent_theme")
        
        # Mock both theme file and default file don't exist
        mock_theme_file = Mock()
        mock_theme_file.exists.return_value = False
        mock_default_file = Mock()
        mock_default_file.exists.return_value = False
        
        with patch('pathlib.Path.__truediv__', side_effect=[mock_theme_file, mock_default_file]):
            content = loader.load_theme()
            assert content == ""

    def test_load_theme_file_read_error(self):
        """Test load_theme method with file read error."""
        loader = ThemeLoader("test_theme")
        
        mock_file = Mock()
        mock_file.exists.return_value = True
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            with patch('builtins.open', side_effect=IOError("File read error")):
                content = loader.load_theme()
                assert content == ""

    def test_apply_theme_with_content(self):
        """Test apply_theme method with QSS content."""
        loader = ThemeLoader("test_theme")
        test_content = "QWidget { background-color: red; }"
        
        with patch.object(loader, 'load_theme', return_value=test_content):
            with patch.object(self.app, 'setStyleSheet') as mock_set_style:
                loader.apply_theme(self.app)
                mock_set_style.assert_called_once_with(test_content)

    def test_apply_theme_empty_content(self):
        """Test apply_theme method with empty content."""
        loader = ThemeLoader("test_theme")
        
        with patch.object(loader, 'load_theme', return_value=""):
            with patch.object(self.app, 'setStyleSheet') as mock_set_style:
                loader.apply_theme(self.app)
                mock_set_style.assert_not_called()

    def test_apply_theme_to_widget_with_content(self):
        """Test apply_theme_to_widget method with QSS content."""
        loader = ThemeLoader("test_theme")
        test_content = "QWidget { background-color: red; }"
        mock_widget = Mock()
        
        with patch.object(loader, 'load_theme', return_value=test_content):
            with patch.object(mock_widget, 'setStyleSheet') as mock_set_style:
                loader.apply_theme_to_widget(mock_widget)
                mock_set_style.assert_called_once_with(test_content)

    def test_apply_theme_to_widget_empty_content(self):
        """Test apply_theme_to_widget method with empty content."""
        loader = ThemeLoader("test_theme")
        mock_widget = Mock()
        
        with patch.object(loader, 'load_theme', return_value=""):
            with patch.object(mock_widget, 'setStyleSheet') as mock_set_style:
                loader.apply_theme_to_widget(mock_widget)
                mock_set_style.assert_not_called()

    def test_apply_theme_exception(self):
        """Test apply_theme method with exception."""
        loader = ThemeLoader("test_theme")
        
        with patch.object(loader, 'load_theme', side_effect=Exception("Load error")):
            with patch.object(self.app, 'setStyleSheet') as mock_set_style:
                # Should not raise exception
                loader.apply_theme(self.app)
                mock_set_style.assert_not_called()

    def test_apply_theme_to_widget_exception(self):
        """Test apply_theme_to_widget method with exception."""
        loader = ThemeLoader("test_theme")
        mock_widget = Mock()
        
        with patch.object(loader, 'load_theme', side_effect=Exception("Load error")):
            with patch.object(mock_widget, 'setStyleSheet') as mock_set_style:
                # Should not raise exception
                loader.apply_theme_to_widget(mock_widget)
                mock_set_style.assert_not_called()

    def test_theme_dir_path(self):
        """Test that theme_dir is correctly set."""
        loader = ThemeLoader()
        actual_path = str(loader.theme_dir)
        # Normalize case and separators to be robust across CI paths
        normalized = actual_path.replace('\\', '/').lower()
        # Only assert the stable suffix so code is not forced by tests to match absolute layout
        assert normalized.endswith('src/markdownall/ui/pyside/styles/themes') or normalized.endswith('markdownall/ui/pyside/styles/themes')

    def test_load_theme_encoding(self):
        """Test load_theme method uses correct encoding."""
        loader = ThemeLoader("test_theme")
        test_content = "QWidget { background-color: red; }"
        
        mock_file = Mock()
        mock_file.exists.return_value = True
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            with patch('builtins.open', mock_open(read_data=test_content)) as mock_file_open:
                loader.load_theme()
                # Verify file was opened with UTF-8 encoding
                mock_file_open.assert_called_once()
                call_args = mock_file_open.call_args
                assert 'encoding' in call_args[1]
                assert call_args[1]['encoding'] == 'utf-8'

    def test_theme_name_property(self):
        """Test theme_name property can be accessed."""
        loader = ThemeLoader("custom_theme")
        assert loader.theme_name == "custom_theme"
        
        # Should be able to modify
        loader.theme_name = "another_theme"
        assert loader.theme_name == "another_theme"

    def test_theme_dir_property(self):
        """Test theme_dir property can be accessed."""
        loader = ThemeLoader()
        assert loader.theme_dir is not None
        assert hasattr(loader.theme_dir, 'name')
        assert loader.theme_dir.name == "themes"
