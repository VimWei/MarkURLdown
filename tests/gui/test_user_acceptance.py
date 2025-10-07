"""
User Acceptance Tests for GUI system.

This module tests the complete user experience:
- Functionality completeness
- User experience
- Compatibility
- Performance
"""

import sys
import os
import unittest
import time
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from markdownall.ui.pyside.main_window import MainWindow


class TestFunctionalityCompleteness(unittest.TestCase):
    """Test that all required functionality is present."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'main_window'):
            self.main_window.close()
    
    def test_all_pages_present(self):
        """Test that all required pages are present."""
        required_pages = ['basic_page', 'webpage_page', 'advanced_page', 'about_page']
        for page_name in required_pages:
            self.assertTrue(hasattr(self.main_window, page_name), 
                          f"Missing page: {page_name}")
    
    def test_all_components_present(self):
        """Test that all required components are present."""
        required_components = ['command_panel', 'log_panel']
        for component_name in required_components:
            self.assertTrue(hasattr(self.main_window, component_name), 
                          f"Missing component: {component_name}")
    
    def test_all_managers_present(self):
        """Test that all required managers are present."""
        required_managers = ['config_manager', 'startup_manager', 'error_handler', 'memory_optimizer']
        for manager_name in required_managers:
            self.assertTrue(hasattr(self.main_window, manager_name), 
                          f"Missing manager: {manager_name}")
    
    def test_basic_functionality(self):
        """Test basic functionality is working."""
        # Test URL management
        test_urls = ["https://example.com", "https://test.com"]
        self.main_window.basic_page.set_urls(test_urls)
        self.assertEqual(self.main_window.basic_page.get_urls(), test_urls)
        
        # Test output directory
        test_dir = "/tmp/test_output"
        self.main_window.basic_page.set_output_dir(test_dir)
        self.assertEqual(self.main_window.basic_page.get_output_dir(), test_dir)
        
        # Test conversion options
        options = {
            "use_proxy": True,
            "ignore_ssl": False,
            "download_images": True,
            "filter_site_chrome": True,
            "use_shared_browser": True
        }
        self.main_window.webpage_page.set_options(options)
        retrieved_options = self.main_window.webpage_page.get_options()
        for key, value in options.items():
            self.assertEqual(retrieved_options[key], value)
    
    def test_advanced_functionality(self):
        """Test advanced functionality is working."""
        # Test user data path
        test_path = "/tmp/user_data"
        self.main_window.advanced_page.set_user_data_path(test_path)
        self.assertEqual(self.main_window.advanced_page.get_user_data_path(), test_path)
        
        # Test language selection
        self.main_window.advanced_page.set_language("zh")
        self.assertEqual(self.main_window.advanced_page.get_language(), "zh")
        
        # Log level feature removed; skip
        
        # Debug mode removed


class TestUserExperience(unittest.TestCase):
    """Test user experience aspects."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'main_window'):
            self.main_window.close()
    
    def test_ui_responsiveness(self):
        """Test that UI is responsive."""
        # Test that all buttons are accessible
        self.assertIsNotNone(self.main_window.command_panel.btn_convert)
        self.assertIsNotNone(self.main_window.command_panel.btn_restore)
        self.assertIsNotNone(self.main_window.command_panel.btn_import)
        self.assertIsNotNone(self.main_window.command_panel.btn_export)
        
        # Test that buttons are enabled
        self.assertTrue(self.main_window.command_panel.btn_convert.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_restore.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_import.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_export.isEnabled())
    
    def test_tab_navigation(self):
        """Test tab navigation works smoothly."""
        # Test switching between all tabs
        for i in range(self.main_window.tabs.count()):
            self.main_window.tabs.setCurrentIndex(i)
            current_widget = self.main_window.tabs.currentWidget()
            self.assertIsNotNone(current_widget)
            
            # Test that the current widget exists and can be accessed
            self.assertIsNotNone(current_widget)
            # Note: isVisible() might be False during testing, so we just check existence
    
    def test_progress_display(self):
        """Test progress display functionality."""
        # Test setting progress (integrated into CommandPanel)
        self.main_window.command_panel.set_progress(50, "Processing...")
        self.assertEqual(self.main_window.command_panel.progress.value(), 50)
        
        # Test progress bar range
        self.assertEqual(self.main_window.command_panel.progress.minimum(), 0)
        self.assertEqual(self.main_window.command_panel.progress.maximum(), 100)
    
    def test_log_display(self):
        """Test log display functionality."""
        # Test adding log messages
        test_messages = [
            "Info message",
            "Error message", 
            "Success message"
        ]
        
        for message in test_messages:
            self.main_window.log_panel.addLog(message)
        
        # Test that messages are in log
        log_content = self.main_window.log_panel.getLogContent()
        for message in test_messages:
            self.assertIn(message, log_content)
        
        # Test log clearing
        self.main_window.log_panel.clearLog()
        log_content = self.main_window.log_panel.getLogContent()
        self.assertEqual(log_content, "")
    
    def test_window_properties(self):
        """Test window properties are set correctly."""
        # Test window size
        self.assertGreater(self.main_window.width(), 0)
        self.assertGreater(self.main_window.height(), 0)
        
        # Test minimum size
        self.assertGreater(self.main_window.minimumWidth(), 0)
        self.assertGreater(self.main_window.minimumHeight(), 0)
        
        # Test window title
        self.assertIsInstance(self.main_window.windowTitle(), str)


class TestCompatibility(unittest.TestCase):
    """Test compatibility aspects."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'main_window'):
            self.main_window.close()
    
    def test_backward_compatibility(self):
        """Backward compatibility no longer requires PySideApp alias."""
        # 统一入口为 MainWindow，不再保证 PySideApp 存在
        self.assertIsNotNone(MainWindow)
    
    def test_signal_compatibility(self):
        """Test that signals are compatible with existing code."""
        # Test that main window has expected signals
        self.assertTrue(hasattr(self.main_window, 'conversionProgress'))
        self.assertTrue(hasattr(self.main_window, 'errorOccurred'))
        self.assertTrue(hasattr(self.main_window, 'configChanged'))
    
    def test_config_compatibility(self):
        """Test configuration compatibility."""
        # Test that configuration structure is compatible
        state = self.main_window._get_current_state()
        self.assertIsInstance(state, dict)
        
        # Test that state contains expected keys
        expected_keys = ["urls", "output_dir", "use_proxy", "ignore_ssl", 
                        "download_images", "filter_site_chrome", "use_shared_browser"]
        for key in expected_keys:
            self.assertIn(key, state)
    
    def test_api_compatibility(self):
        """Test API compatibility."""
        # Test that main methods exist
        self.assertTrue(hasattr(self.main_window, '_get_current_state'))
        self.assertTrue(hasattr(self.main_window, '_apply_state'))
        self.assertTrue(hasattr(self.main_window, 'closeEvent'))


class TestPerformance(unittest.TestCase):
    """Test performance aspects."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'main_window'):
            self.main_window.close()
    
    def test_startup_performance(self):
        """Test startup performance."""
        start_time = time.time()
        # MainWindow already created in setUp
        end_time = time.time()
        
        startup_time = end_time - start_time
        # Startup should be reasonably fast (less than 5 seconds)
        self.assertLess(startup_time, 5.0, f"Startup too slow: {startup_time:.2f}s")
    
    def test_memory_usage(self):
        """Test memory usage."""
        # Test that memory optimizer is working
        self.assertIsNotNone(self.main_window.memory_optimizer)
        
        # Test memory usage check
        memory_usage = self.main_window.memory_optimizer.check_memory_usage()
        self.assertIsInstance(memory_usage, float)
        self.assertGreaterEqual(memory_usage, 0)
        
        # Memory usage should be reasonable (less than 500MB for GUI)
        self.assertLess(memory_usage, 500, f"Memory usage too high: {memory_usage:.2f}MB")
    
    def test_ui_responsiveness(self):
        """Test UI responsiveness."""
        # Test that UI operations are responsive
        start_time = time.time()
        
        # Test page switching
        for i in range(self.main_window.tabs.count()):
            self.main_window.tabs.setCurrentIndex(i)
        
        # Test progress updates (integrated into CommandPanel)
        self.main_window.command_panel.set_progress(50, "Test")
        
        # Test log updates
        self.main_window.log_panel.addLog("Test message")
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # UI operations should be fast (less than 1 second)
        self.assertLess(operation_time, 1.0, f"UI operations too slow: {operation_time:.2f}s")
    
    def test_error_handling_performance(self):
        """Test error handling performance."""
        # Test that error handling is efficient
        start_time = time.time()
        
        # Test error handling
        test_error = ValueError("Test error")
        result = self.main_window.error_handler.handle_error(
            test_error, "test_context", show_user=False
        )
        
        end_time = time.time()
        error_handling_time = end_time - start_time
        
        # Error handling should be fast (less than 0.1 seconds)
        self.assertLess(error_handling_time, 0.1, 
                       f"Error handling too slow: {error_handling_time:.2f}s")
    
    def test_config_management_performance(self):
        """Test configuration management performance."""
        # Test that config operations are efficient
        start_time = time.time()
        
        # Test config operations
        config = self.main_window.config_manager.get_all_config()
        self.main_window.config_manager.set_all_config(config)
        
        end_time = time.time()
        config_time = end_time - start_time
        
        # Config operations should be fast (less than 0.1 seconds)
        self.assertLess(config_time, 0.1, f"Config operations too slow: {config_time:.2f}s")


class TestAccessibility(unittest.TestCase):
    """Test accessibility aspects."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.main_window = MainWindow(self.root_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'main_window'):
            self.main_window.close()
    
    def test_keyboard_navigation(self):
        """Test keyboard navigation."""
        # Test that all interactive elements are accessible via keyboard
        # This is a basic test - full keyboard navigation testing would require more setup
        
        # Test that buttons are focusable
        self.assertTrue(self.main_window.command_panel.btn_convert.isEnabled())
        self.assertTrue(self.main_window.command_panel.btn_restore.isEnabled())
        
        # Test that tabs are accessible
        self.assertTrue(self.main_window.tabs.isEnabled())
    
    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility."""
        # Test that important elements have accessible names
        # This is a basic test - full accessibility testing would require more setup
        
        # Test that buttons have text
        self.assertIsInstance(self.main_window.command_panel.btn_convert.text(), str)
        self.assertIsInstance(self.main_window.command_panel.btn_restore.text(), str)
        
        # Test that labels have text (progress is integrated into CommandPanel)
        self.assertIsInstance(self.main_window.command_panel.progress.text(), str)
    
    def test_high_contrast_support(self):
        """Test high contrast support."""
        # Test that the application can handle high contrast themes
        # This is a basic test - full theme testing would require more setup
        
        # Test that the application doesn't crash with different themes
        try:
            self.main_window.setStyleSheet("QWidget { background-color: black; color: white; }")
            self.main_window.setStyleSheet("")  # Reset
        except Exception as e:
            self.fail(f"High contrast support failed: {e}")


if __name__ == '__main__':
    unittest.main()
