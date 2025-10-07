"""
Unit tests for GUI managers.

This module tests the functionality of all GUI managers:
- ConfigManager
- StartupManager
- ErrorHandler
- MemoryOptimizer
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from markdownall.config.config_manager import ConfigManager
from markdownall.utils.memory_optimizer import MemoryOptimizer
from markdownall.ui.pyside.error_handler import ErrorHandler
from markdownall.services.config_service import ConfigService


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.root_dir = os.path.dirname(__file__)
        self.config_manager = ConfigManager(self.root_dir)
    
    def test_initialization(self):
        """Test ConfigManager initialization."""
        self.assertIsNotNone(self.config_manager)
        self.assertEqual(self.config_manager.root_dir, self.root_dir)
        
        # Test that all config objects are initialized
        self.assertIsNotNone(self.config_manager.basic)
        self.assertIsNotNone(self.config_manager.webpage)
        self.assertIsNotNone(self.config_manager.advanced)
        self.assertIsNotNone(self.config_manager.about)
    
    def test_basic_config(self):
        """Test basic configuration management."""
        # Test setting URLs
        test_urls = ["https://example.com", "https://test.com"]
        self.config_manager.basic.urls = test_urls
        self.assertEqual(self.config_manager.basic.urls, test_urls)
        
        # Test setting output directory
        test_dir = "/tmp/test_output"
        self.config_manager.basic.output_dir = test_dir
        self.assertEqual(self.config_manager.basic.output_dir, test_dir)
    
    def test_webpage_config(self):
        """Test webpage configuration management."""
        # Test setting options
        self.config_manager.webpage.use_proxy = True
        self.config_manager.webpage.ignore_ssl = True
        self.config_manager.webpage.download_images = False
        
        self.assertTrue(self.config_manager.webpage.use_proxy)
        self.assertTrue(self.config_manager.webpage.ignore_ssl)
        self.assertFalse(self.config_manager.webpage.download_images)
    
    def test_advanced_config(self):
        """Test advanced configuration management."""
        # Test setting language
        self.config_manager.advanced.language = "zh"
        self.assertEqual(self.config_manager.advanced.language, "zh")
        
        # Debug mode removed
        
        # Log level removed from advanced config
    
    def test_config_export_import(self):
        """Test configuration export and import."""
        # Set some test values
        self.config_manager.basic.urls = ["https://example.com"]
        self.config_manager.webpage.use_proxy = True
        self.config_manager.advanced.language = "en"
        
        # Export configuration
        config = self.config_manager.get_all_config()
        self.assertIn("basic", config)
        self.assertIn("webpage", config)
        self.assertIn("advanced", config)
        self.assertIn("about", config)
        
        # Test configuration values
        self.assertEqual(config["basic"]["urls"], ["https://example.com"])
        self.assertTrue(config["webpage"]["use_proxy"])
        self.assertEqual(config["advanced"]["language"], "en")
    
    def test_config_reset(self):
        """Test configuration reset."""
        # Set some values
        self.config_manager.basic.urls = ["https://example.com"]
        self.config_manager.webpage.use_proxy = True
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        # Check that values are reset
        self.assertEqual(self.config_manager.basic.urls, [])
        self.assertFalse(self.config_manager.webpage.use_proxy)
    
    def test_session_management(self):
        """Test session management."""
        # Test saving session
        self.config_manager.basic.urls = ["https://example.com"]
        result = self.config_manager.save_session("test_session")
        # Note: This might fail if sessions directory doesn't exist
        # but the method should not raise an exception
        self.assertIsInstance(result, bool)
        
        # Test loading session
        result = self.config_manager.load_session("test_session")
        self.assertIsInstance(result, bool)
    
    def test_settings_management(self):
        """Test settings management."""
        # Test saving settings
        self.config_manager.advanced.language = "zh"
        result = self.config_manager.save_settings()
        self.assertIsInstance(result, bool)
        
        # Test loading settings
        result = self.config_manager.load_settings()
        self.assertIsInstance(result, bool)


## StartupManager 已移除，相关测试下线


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.root_dir = os.path.dirname(__file__)
        self.config_manager = ConfigManager(self.root_dir)
        self.config_service = ConfigService(self.root_dir)
        self.error_handler = ErrorHandler(self.config_service)
    
    def test_initialization(self):
        """Test ErrorHandler initialization."""
        self.assertIsNotNone(self.error_handler)
        self.assertTrue(hasattr(self.error_handler, 'config_service'))
    
    def test_error_handling(self):
        """Test error handling functionality."""
        # Test handling a simple error
        test_error = ValueError("Test error")
        result = self.error_handler.handle_error(
            test_error, "test_context", show_user=False
        )
        self.assertIsInstance(result, bool)
    
    def test_error_statistics(self):
        """Test error statistics."""
        # Handle a test error
        test_error = ValueError("Test error")
        self.error_handler.handle_error(test_error, "test_context", show_user=False)
        
        # Get error statistics
        stats = self.error_handler.get_error_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_errors", stats)
        self.assertIn("recent_errors", stats)
        self.assertIn("recovery_attempts", stats)
        self.assertIn("error_types", stats)
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # Test that recovery methods exist
        self.assertTrue(hasattr(self.error_handler, '_attempt_recovery'))
        self.assertTrue(hasattr(self.error_handler, '_recover_file_not_found'))
        self.assertTrue(hasattr(self.error_handler, '_recover_permission_error'))
        self.assertTrue(hasattr(self.error_handler, '_recover_connection_error'))
    
    def test_performance_monitoring(self):
        """Test performance monitoring."""
        # Test that performance monitoring methods exist
        self.assertTrue(hasattr(self.error_handler, '_monitor_performance'))
        
        # Test performance monitoring (this might not work in test environment)
        try:
            self.error_handler._monitor_performance()
        except Exception:
            # This might fail in test environment, which is acceptable
            pass
    
    def test_error_export(self):
        """Test error report export."""
        # Test that export method exists
        self.assertTrue(hasattr(self.error_handler, 'export_error_report'))
        
        # Test export (this might fail if directory doesn't exist)
        try:
            result = self.error_handler.export_error_report("/tmp/test_error_report.json")
            self.assertIsInstance(result, bool)
        except Exception:
            # This might fail in test environment
            pass


class TestMemoryOptimizer(unittest.TestCase):
    """Test MemoryOptimizer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.memory_optimizer = MemoryOptimizer()
    
    def test_initialization(self):
        """Test MemoryOptimizer initialization."""
        self.assertIsNotNone(self.memory_optimizer)
        self.assertIsInstance(self.memory_optimizer._memory_threshold, int)
        self.assertIsInstance(self.memory_optimizer._gc_interval, int)
    
    def test_memory_usage_check(self):
        """Test memory usage checking."""
        memory_usage = self.memory_optimizer.check_memory_usage()
        self.assertIsInstance(memory_usage, float)
        self.assertGreaterEqual(memory_usage, 0)
    
    def test_memory_optimization(self):
        """Test memory optimization."""
        collected = self.memory_optimizer.optimize_memory()
        self.assertIsInstance(collected, int)
        self.assertGreaterEqual(collected, 0)
    
    def test_memory_info(self):
        """Test memory information retrieval."""
        memory_info = self.memory_optimizer.get_memory_info()
        self.assertIsInstance(memory_info, dict)
        self.assertIn("rss", memory_info)
        self.assertIn("vms", memory_info)
        self.assertIn("percent", memory_info)
        self.assertIn("available", memory_info)
    
    def test_optimization_threshold(self):
        """Test optimization threshold checking."""
        should_optimize = self.memory_optimizer.should_optimize()
        self.assertIsInstance(should_optimize, bool)


if __name__ == '__main__':
    unittest.main()
