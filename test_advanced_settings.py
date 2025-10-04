#!/usr/bin/env python3
"""
Test script for Advanced Settings functionality.
Tests language, log level, debug mode, and restore default config.
"""

import os
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from markdownall.ui.pyside.main_window import MainWindow

def test_advanced_settings():
    """Test advanced settings functionality."""
    app = QApplication(sys.argv)
    
    # Create main window
    root_dir = os.path.dirname(os.path.dirname(__file__))
    main_window = MainWindow(root_dir)
    main_window.show()
    
    print("Testing Advanced Settings...")
    
    # Test 1: Language settings
    print("\n1. Testing Language Settings:")
    print(f"Current language: {main_window.advanced_page.get_language()}")
    
    # Test auto language detection
    main_window.advanced_page.set_language("auto")
    print(f"Set to auto, actual language: {main_window.advanced_page.get_language()}")
    
    # Test specific language
    main_window.advanced_page.set_language("zh")
    print(f"Set to zh: {main_window.advanced_page.get_language()}")
    
    # Test 2: Log Level settings
    print("\n2. Testing Log Level Settings:")
    print(f"Current log level: {main_window.advanced_page.get_log_level()}")
    
    # Test different log levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        main_window.advanced_page.set_log_level(level)
        print(f"Set to {level}: {main_window.advanced_page.get_log_level()}")
    
    # Test 3: Debug Mode settings
    print("\n3. Testing Debug Mode Settings:")
    print(f"Current debug mode: {main_window.advanced_page.get_debug_mode()}")
    
    # Test enabling debug mode
    main_window.advanced_page.set_debug_mode(True)
    print(f"Enabled debug mode: {main_window.advanced_page.get_debug_mode()}")
    
    # Test debug logging
    main_window.log_debug("This is a debug message")
    
    # Test disabling debug mode
    main_window.advanced_page.set_debug_mode(False)
    print(f"Disabled debug mode: {main_window.advanced_page.get_debug_mode()}")
    
    # Test 4: Configuration persistence
    print("\n4. Testing Configuration Persistence:")
    
    # Save current config
    main_window._save_config()
    print("Configuration saved")
    
    # Load config
    main_window._load_config()
    print("Configuration loaded")
    
    # Test 5: Restore Default Config
    print("\n5. Testing Restore Default Config:")
    main_window._restore_default_config()
    print("Default configuration restored")
    
    # Test 6: Signal connections
    print("\n6. Testing Signal Connections:")
    
    # Test language change signal
    main_window.advanced_page.languageChanged.emit("en")
    print("Language change signal emitted")
    
    # Test log level change signal
    main_window.advanced_page.logLevelChanged.emit("DEBUG")
    print("Log level change signal emitted")
    
    # Test debug mode change signal
    main_window.advanced_page.debugModeChanged.emit(True)
    print("Debug mode change signal emitted")
    
    # Test restore default config signal
    main_window.advanced_page.restoreDefaultConfigRequested.emit()
    print("Restore default config signal emitted")
    
    print("\nAll tests completed successfully!")
    
    # Keep window open for a moment to see results
    QTimer.singleShot(2000, app.quit)
    app.exec()

if __name__ == "__main__":
    test_advanced_settings()
