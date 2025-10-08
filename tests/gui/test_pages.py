"""
Unit tests for GUI pages.

This module tests the functionality of all GUI pages:
- BasicPage
- WebpagePage
- AdvancedPage
- AboutPage
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from markdownall.ui.pyside.main_window import Translator
from markdownall.ui.pyside.pages.about_page import AboutPage
from markdownall.ui.pyside.pages.advanced_page import AdvancedPage
from markdownall.ui.pyside.pages.basic_page import BasicPage
from markdownall.ui.pyside.pages.webpage_page import WebpagePage


class TestBasicPage(unittest.TestCase):
    """Test BasicPage functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        # Use real QWidget as parent, mock translator
        self.parent = QWidget()
        self.translator = Mock()
        self.translator.t = lambda key: key  # Mock translation function

        self.page = BasicPage(self.parent, self.translator)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "page"):
            self.page.close()

    def test_initialization(self):
        """Test page initialization."""
        self.assertIsNotNone(self.page)
        self.assertEqual(self.page.parent(), self.parent)
        self.assertEqual(self.page.translator, self.translator)

    def test_url_management(self):
        """Test URL list management."""
        # Test adding URLs
        test_urls = ["https://example.com", "https://test.com"]
        self.page.set_urls(test_urls)
        self.assertEqual(self.page.get_urls(), test_urls)

        # Test clearing URLs
        self.page.clear_urls()
        self.assertEqual(self.page.get_urls(), [])

    def test_output_directory(self):
        """Test output directory management."""
        test_dir = "/tmp/test_output"
        self.page.set_output_dir(test_dir)
        self.assertEqual(self.page.get_output_dir(), test_dir)

    def test_config_management(self):
        """Test configuration management."""
        config = {"urls": ["https://example.com"], "output_dir": "/tmp/test"}
        self.page.set_config(config)

        retrieved_config = self.page.get_config()
        self.assertEqual(retrieved_config["urls"], config["urls"])
        self.assertEqual(retrieved_config["output_dir"], config["output_dir"])

    def test_signals(self):
        """Test signal emissions."""
        # Test URL list changed signal
        with patch.object(self.page, "urlListChanged") as mock_signal:
            self.page.set_urls(["https://example.com"])
            # Signal should be emitted when URLs change
            # Note: This depends on the actual implementation

    def test_retranslate_ui(self):
        """Test UI retranslation."""
        # This should not raise an exception
        self.page.retranslate_ui()


class TestWebpagePage(unittest.TestCase):
    """Test WebpagePage functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        # Use real QWidget as parent, mock translator
        self.parent = QWidget()
        self.translator = Mock()
        self.translator.t = lambda key: key

        self.page = WebpagePage(self.parent, self.translator)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "page"):
            self.page.close()

    def test_initialization(self):
        """Test page initialization."""
        self.assertIsNotNone(self.page)
        self.assertEqual(self.page.parent(), self.parent)
        self.assertEqual(self.page.translator, self.translator)

    def test_options_management(self):
        """Test conversion options management."""
        # Test setting options
        options = {
            "use_proxy": True,
            "ignore_ssl": True,
            "download_images": False,
            "filter_site_chrome": False,
            "use_shared_browser": False,
        }
        self.page.set_options(options)

        # Test getting options
        retrieved_options = self.page.get_options()
        for key, value in options.items():
            self.assertEqual(retrieved_options[key], value)

    def test_config_management(self):
        """Test configuration management."""
        config = {
            "use_proxy": True,
            "ignore_ssl": False,
            "download_images": True,
            "filter_site_chrome": True,
            "use_shared_browser": True,
        }
        self.page.set_config(config)

        retrieved_config = self.page.get_config()
        for key, value in config.items():
            self.assertEqual(retrieved_config[key], value)

    def test_retranslate_ui(self):
        """Test UI retranslation."""
        self.page.retranslate_ui()


class TestAdvancedPage(unittest.TestCase):
    """Test AdvancedPage functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        # Use real QWidget as parent, mock translator
        self.parent = QWidget()
        self.translator = Mock()
        self.translator.t = lambda key: key

        self.page = AdvancedPage(self.parent, self.translator)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "page"):
            self.page.close()

    def test_initialization(self):
        """Test page initialization."""
        self.assertIsNotNone(self.page)
        self.assertEqual(self.page.parent(), self.parent)
        self.assertEqual(self.page.translator, self.translator)

    def test_user_data_path(self):
        """Test user data path management."""
        test_path = "/tmp/user_data"
        self.page.set_user_data_path(test_path)
        self.assertEqual(self.page.get_user_data_path(), test_path)

    def test_language_selection(self):
        """Test language selection."""
        test_language = "zh"
        self.page.set_language(test_language)
        self.assertEqual(self.page.get_language(), test_language)

    def test_log_level_removed(self):
        """Log level feature removed; ensure methods no longer exist."""
        self.assertFalse(hasattr(self.page, "set_log_level"))
        self.assertFalse(hasattr(self.page, "get_log_level"))

    def test_debug_mode_removed(self):
        """Debug mode removed; methods should not exist."""
        self.assertFalse(hasattr(self.page, "set_debug_mode"))
        self.assertFalse(hasattr(self.page, "get_debug_mode"))

    def test_config_management(self):
        """Test configuration management."""
        config = {
            "user_data_path": "/tmp/data",
            "language": "en",
            # debug_mode removed
        }
        self.page.set_config(config)

        retrieved_config = self.page.get_config()
        for key, value in config.items():
            self.assertEqual(retrieved_config[key], value)
        self.assertNotIn("debug_mode", retrieved_config)
        self.assertNotIn("log_level", retrieved_config)

    def test_retranslate_ui(self):
        """Test UI retranslation."""
        self.page.retranslate_ui()


class TestAboutPage(unittest.TestCase):
    """Test AboutPage functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        # Use real QWidget as parent, mock translator
        self.parent = QWidget()
        self.translator = Mock()
        self.translator.t = lambda key: key

        self.page = AboutPage(self.parent, self.translator)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "page"):
            self.page.close()

    def test_initialization(self):
        """Test page initialization."""
        self.assertIsNotNone(self.page)
        self.assertEqual(self.page.parent(), self.parent)
        self.assertEqual(self.page.translator, self.translator)

    def test_config_management(self):
        """Test configuration management."""
        config = {"homepage_clicked": True, "last_update_check": "2024-01-01"}
        self.page.set_config(config)

        retrieved_config = self.page.get_config()
        for key, value in config.items():
            self.assertEqual(retrieved_config[key], value)

    def test_retranslate_ui(self):
        """Test UI retranslation."""
        self.page.retranslate_ui()


class TestTranslator(unittest.TestCase):
    """Test Translator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Get the correct path to locales directory
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up to project root
        self.locales_dir = os.path.join(project_root, "src", "markdownall", "ui", "locales")
        self.translator = Translator(self.locales_dir)

    def test_load_language(self):
        """Test language loading."""
        # Test loading English
        self.translator.load_language("en")
        self.assertEqual(self.translator.language, "en")

        # Test loading Chinese
        self.translator.load_language("zh")
        self.assertEqual(self.translator.language, "zh")

    def test_translation(self):
        """Test translation functionality."""
        self.translator.load_language("en")

        # Test English translation
        en_text = self.translator.t("url_label")
        self.assertIsInstance(en_text, str)

        # Test Chinese translation
        self.translator.load_language("zh")
        zh_text = self.translator.t("url_label")
        self.assertIsInstance(zh_text, str)

        # Chinese and English should be different
        self.assertNotEqual(en_text, zh_text)


if __name__ == "__main__":
    unittest.main()
