"""
Integration tests for GUI system.

This module tests the integration between different components:
- Page switching
- Conversion workflow
- Session management
- Internationalization
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from markdownall.ui.pyside.components import CommandPanel, LogPanel
from markdownall.ui.pyside.main_window import MainWindow
from markdownall.ui.pyside.pages import AboutPage, AdvancedPage, BasicPage, WebpagePage


class TestPageSwitching(unittest.TestCase):
    """Test page switching functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_page_creation(self):
        """Test that all pages are created."""
        self.assertIsNotNone(self.main_window.basic_page)
        self.assertIsNotNone(self.main_window.webpage_page)
        self.assertIsNotNone(self.main_window.advanced_page)
        self.assertIsNotNone(self.main_window.about_page)

        # Test that pages are instances of correct classes
        self.assertIsInstance(self.main_window.basic_page, BasicPage)
        self.assertIsInstance(self.main_window.webpage_page, WebpagePage)
        self.assertIsInstance(self.main_window.advanced_page, AdvancedPage)
        self.assertIsInstance(self.main_window.about_page, AboutPage)

    def test_tab_structure(self):
        """Test tab widget structure."""
        self.assertIsNotNone(self.main_window.tabs)
        self.assertEqual(self.main_window.tabs.count(), 4)

        # Test tab titles
        tab_titles = []
        for i in range(self.main_window.tabs.count()):
            tab_titles.append(self.main_window.tabs.tabText(i))

        # Check for Chinese tab titles (actual implementation)
        self.assertIn("基础", tab_titles)
        self.assertIn("网页", tab_titles)
        self.assertIn("高级", tab_titles)
        self.assertIn("关于", tab_titles)

    def test_page_switching(self):
        """Test switching between pages."""
        # Test switching to each page
        for i in range(self.main_window.tabs.count()):
            self.main_window.tabs.setCurrentIndex(i)
            current_widget = self.main_window.tabs.currentWidget()
            self.assertIsNotNone(current_widget)

    def test_page_signals(self):
        """Test that page signals are connected."""
        # Test basic page signals
        self.assertTrue(hasattr(self.main_window.basic_page, "urlListChanged"))
        self.assertTrue(hasattr(self.main_window.basic_page, "outputDirChanged"))

        # Test webpage page signals
        self.assertTrue(hasattr(self.main_window.webpage_page, "optionsChanged"))

        # Test advanced page signals
        self.assertTrue(hasattr(self.main_window.advanced_page, "openUserDataRequested"))
        self.assertTrue(hasattr(self.main_window.advanced_page, "restoreDefaultConfigRequested"))
        self.assertTrue(hasattr(self.main_window.advanced_page, "languageChanged"))

        # Test about page signals
        self.assertTrue(hasattr(self.main_window.about_page, "checkUpdatesRequested"))
        self.assertTrue(hasattr(self.main_window.about_page, "openHomepageRequested"))


class TestComponentIntegration(unittest.TestCase):
    """Test component integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_component_creation(self):
        """Test that all components are created."""
        self.assertIsNotNone(self.main_window.command_panel)
        self.assertIsNotNone(self.main_window.log_panel)

        # Test that components are instances of correct classes
        self.assertIsInstance(self.main_window.command_panel, CommandPanel)
        self.assertIsInstance(self.main_window.log_panel, LogPanel)

    def test_splitter_structure(self):
        """Test splitter widget structure."""
        self.assertIsNotNone(self.main_window.splitter)
        self.assertEqual(self.main_window.splitter.count(), 3)

        # Test that all components are in the splitter
        widgets = []
        for i in range(self.main_window.splitter.count()):
            widgets.append(self.main_window.splitter.widget(i))

        self.assertIn(self.main_window.tabs, widgets)
        self.assertIn(self.main_window.command_panel, widgets)
        self.assertIn(self.main_window.log_panel, widgets)

    def test_component_signals(self):
        """Test that component signals are connected."""
        # Test command panel signals
        self.assertTrue(hasattr(self.main_window.command_panel, "restoreRequested"))
        self.assertTrue(hasattr(self.main_window.command_panel, "importRequested"))
        self.assertTrue(hasattr(self.main_window.command_panel, "exportRequested"))
        self.assertTrue(hasattr(self.main_window.command_panel, "convertRequested"))
        self.assertTrue(hasattr(self.main_window.command_panel, "stopRequested"))

        # Progress functionality is integrated into CommandPanel

        # Test log panel signals
        self.assertTrue(hasattr(self.main_window.log_panel, "logCleared"))
        self.assertTrue(hasattr(self.main_window.log_panel, "logCopied"))


class TestConversionWorkflow(unittest.TestCase):
    """Test conversion workflow integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_conversion_setup(self):
        """Test conversion setup workflow."""
        # Test setting URLs
        test_urls = ["https://example.com", "https://test.com"]
        self.main_window.basic_page.set_urls(test_urls)
        self.assertEqual(self.main_window.basic_page.get_urls(), test_urls)

        # Test setting output directory
        test_dir = "/tmp/test_output"
        self.main_window.basic_page.set_output_dir(test_dir)
        self.assertEqual(self.main_window.basic_page.get_output_dir(), test_dir)

        # Test setting conversion options
        options = {
            "use_proxy": True,
            "ignore_ssl": False,
            "download_images": True,
            "filter_site_chrome": True,
            "use_shared_browser": True,
        }
        self.main_window.webpage_page.set_options(options)
        retrieved_options = self.main_window.webpage_page.get_options()
        for key, value in options.items():
            self.assertEqual(retrieved_options[key], value)

    def test_progress_tracking(self):
        """Test progress tracking integration."""
        # Test setting progress (integrated into CommandPanel)
        self.main_window.command_panel.set_progress(50, "Processing...")
        self.assertEqual(self.main_window.command_panel.progress.value(), 50)

        # Test log integration
        test_message = "Test log message"
        self.main_window.log_panel.addLog(test_message)
        log_content = self.main_window.log_panel.getLogContent()
        self.assertIn(test_message, log_content)

    def test_conversion_control(self):
        """Test conversion control integration."""
        # Test that conversion control is accessible (single toggle button)
        self.assertIsNotNone(self.main_window.command_panel.btn_convert)
        self.assertTrue(self.main_window.command_panel.btn_convert.isEnabled())
        # Toggle converting state to mimic stop mode
        self.main_window.command_panel.setConvertingState(True)
        self.assertTrue(self.main_window.command_panel._is_converting)
        self.main_window.command_panel.setConvertingState(False)
        self.assertFalse(self.main_window.command_panel._is_converting)


class TestSessionManagement(unittest.TestCase):
    """Test session management integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_session_state_management(self):
        """Test session state management."""
        # Test getting current state
        state = self.main_window._get_current_state()
        self.assertIsInstance(state, dict)

        # Test that state contains expected keys
        expected_keys = [
            "urls",
            "output_dir",
            "use_proxy",
            "ignore_ssl",
            "download_images",
            "filter_site_chrome",
            "use_shared_browser",
        ]
        for key in expected_keys:
            self.assertIn(key, state)

    def test_config_management(self):
        """Test configuration management."""
        # Access via service layer in new architecture
        self.assertIsNotNone(self.main_window.config_service)
        cm = self.main_window.config_service.config_manager
        self.assertTrue(hasattr(cm, "save_session"))
        self.assertTrue(hasattr(cm, "load_session"))
        self.assertTrue(hasattr(cm, "get_all_config"))
        self.assertTrue(hasattr(cm, "set_all_config"))

    def test_session_buttons(self):
        """Test session management buttons."""
        # Test that session buttons are accessible
        self.assertIsNotNone(self.main_window.command_panel.btn_restore)
        self.assertIsNotNone(self.main_window.command_panel.btn_import)
        self.assertIsNotNone(self.main_window.command_panel.btn_export)

        # Test button states
        self.assertTrue(self.main_window.command_panel.btn_restore.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_import.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_export.isEnabled())


class TestInternationalization(unittest.TestCase):
    """Test internationalization integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_translator_integration(self):
        """Test translator integration."""
        # Test that translator is accessible
        self.assertIsNotNone(self.main_window.translator)

        # Test that translator has expected methods
        self.assertTrue(hasattr(self.main_window.translator, "load_language"))
        self.assertTrue(hasattr(self.main_window.translator, "t"))

    def test_language_switching(self):
        """Test language switching."""
        # Test loading English
        self.main_window.translator.load_language("en")
        self.assertEqual(self.main_window.translator.language, "en")

        # Test loading Chinese
        self.main_window.translator.load_language("zh")
        self.assertEqual(self.main_window.translator.language, "zh")

    def test_retranslation(self):
        """Test UI retranslation."""
        # Test that retranslate_ui method exists and can be called
        self.assertTrue(hasattr(self.main_window, "_retranslate_ui"))

        # Test retranslation (this should not raise an exception)
        try:
            self.main_window._retranslate_ui()
        except Exception as e:
            self.fail(f"Retranslation failed: {e}")

    def test_translation_keys(self):
        """Test that translation keys are available."""
        # Test that translation function works
        t = self.main_window.translator.t

        # Test some key translations
        self.assertIsInstance(t("tab_basic"), str)
        self.assertIsInstance(t("tab_advanced"), str)
        self.assertIsInstance(t("command_convert"), str)
        self.assertIsInstance(t("log_clear"), str)


class TestErrorHandling(unittest.TestCase):
    """Test error handling integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "main_window"):
            self.main_window.close()

    def test_error_handler_integration(self):
        """Test error handler integration."""
        # Test that error handler is accessible
        self.assertIsNotNone(self.main_window.error_handler)

        # Test that error handler has expected methods
        self.assertTrue(hasattr(self.main_window.error_handler, "handle_error"))
        self.assertTrue(hasattr(self.main_window.error_handler, "get_error_stats"))

    def test_error_signal_handlers(self):
        """Test error signal handlers."""
        # Test that error signal handlers exist
        self.assertTrue(hasattr(self.main_window, "_on_error_occurred"))
        self.assertTrue(hasattr(self.main_window, "_on_performance_warning"))

    def test_startup_error_handling(self):
        """Test startup error handling."""
        # StartupManager removed; ensure error handler exists instead
        self.assertTrue(hasattr(self.main_window, "error_handler"))


if __name__ == "__main__":
    unittest.main()
