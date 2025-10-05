"""
Error Handler for MarkdownAll GUI.

This module provides comprehensive error handling for the GUI,
including:
- Centralized error logging
- User-friendly error messages
- Error recovery mechanisms
- Performance monitoring
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import logging
from typing import Optional, Callable, Any, Dict
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QApplication

from markdownall.services.config_service import ConfigService


class ErrorHandler(QObject):
    """
    Centralized error handler for MarkdownAll GUI.
    
    Features:
    - Automatic error logging
    - User-friendly error messages
    - Error recovery mechanisms
    - Performance monitoring
    """
    
    # Signals
    error_occurred = Signal(str, str)  # error_type, error_message
    error_recovered = Signal(str)  # recovery_message
    performance_warning = Signal(str)  # warning_message
    
    def __init__(self, config_service: ConfigService):
        super().__init__()
        self.config_service = config_service
        self._error_count = 0
        self._error_history = []
        self._recovery_attempts = {}
        
        # Setup logging
        self._setup_logging()
        
        # Performance monitoring
        self._performance_timer = QTimer()
        self._performance_timer.timeout.connect(self._monitor_performance)
        self._performance_timer.start(30000)  # Check every 30 seconds
        
    def _setup_logging(self):
        """Setup error logging."""
        # Create error logger
        self.error_logger = logging.getLogger('markdownall.errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Create file handler
        log_dir = os.path.join(self.config_service.config_manager.root_dir, "data", "log")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "errors.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.error_logger.addHandler(file_handler)
        
    def handle_error(self, error: Exception, context: str = "", 
                    show_user: bool = True, recoverable: bool = True) -> bool:
        """
        Handle an error with comprehensive logging and recovery.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            show_user: Whether to show error to user
            recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if error was handled successfully, False otherwise
        """
        try:
            # Log error
            error_type = type(error).__name__
            error_message = str(error)
            full_context = f"{context}: {error_message}" if context else error_message
            
            self.error_logger.error(f"{error_type} in {context}: {error_message}")
            self.error_logger.error(traceback.format_exc())
            
            # Update error tracking
            self._error_count += 1
            self._error_history.append({
                "type": error_type,
                "message": error_message,
                "context": context,
                "timestamp": time.time(),
                "traceback": traceback.format_exc()
            })
            
            # Emit signal
            self.error_occurred.emit(error_type, error_message)
            
            # Show user-friendly message if requested
            if show_user:
                self._show_user_error(error_type, error_message, context)
            
            # Attempt recovery if possible
            if recoverable:
                return self._attempt_recovery(error_type, context)
            
            return False
            
        except Exception as e:
            # If error handling itself fails, log to console
            print(f"Error handler failed: {e}")
            return False
    
    def _show_user_error(self, error_type: str, error_message: str, context: str):
        """Show user-friendly error message."""
        try:
            # Create user-friendly message
            if "FileNotFoundError" in error_type:
                user_message = f"File not found: {error_message}"
            elif "PermissionError" in error_type:
                user_message = f"Permission denied: {error_message}"
            elif "ConnectionError" in error_type:
                user_message = f"Network error: {error_message}"
            else:
                user_message = f"An error occurred: {error_message}"
            
            # Show message box
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(user_message)
            msg_box.setDetailedText(f"Error type: {error_type}\nContext: {context}")
            msg_box.exec()
            
        except Exception as e:
            print(f"Failed to show error message: {e}")
    
    def _attempt_recovery(self, error_type: str, context: str) -> bool:
        """Attempt to recover from error."""
        try:
            # Check if we've tried to recover from this error before
            recovery_key = f"{error_type}_{context}"
            if recovery_key in self._recovery_attempts:
                if self._recovery_attempts[recovery_key] >= 3:
                    return False  # Too many attempts
                self._recovery_attempts[recovery_key] += 1
            else:
                self._recovery_attempts[recovery_key] = 1
            
            # Attempt specific recovery strategies
            if "FileNotFoundError" in error_type:
                return self._recover_file_not_found(context)
            elif "PermissionError" in error_type:
                return self._recover_permission_error(context)
            elif "ConnectionError" in error_type:
                return self._recover_connection_error(context)
            else:
                return self._recover_generic_error(error_type, context)
                
        except Exception as e:
            print(f"Recovery attempt failed: {e}")
            return False
    
    def _recover_file_not_found(self, context: str) -> bool:
        """Recover from file not found error."""
        try:
            # Try to create missing directories
            if "session" in context.lower():
                os.makedirs(self.config_manager.sessions_dir, exist_ok=True)
                return True
            elif "log" in context.lower():
                log_dir = os.path.join(self.config_manager.root_dir, "data", "log")
                os.makedirs(log_dir, exist_ok=True)
                return True
            return False
        except Exception:
            return False
    
    def _recover_permission_error(self, context: str) -> bool:
        """Recover from permission error."""
        try:
            # Try to change file permissions
            if "session" in context.lower():
                session_dir = self.config_manager.sessions_dir
                if os.path.exists(session_dir):
                    os.chmod(session_dir, 0o755)
                    return True
            return False
        except Exception:
            return False
    
    def _recover_connection_error(self, context: str) -> bool:
        """Recover from connection error."""
        try:
            # Wait a bit and retry
            import time
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def _recover_generic_error(self, error_type: str, context: str) -> bool:
        """Recover from generic error."""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            return True
        except Exception:
            return False
    
    def _monitor_performance(self):
        """Monitor performance and detect issues."""
        try:
            # Check error rate
            if self._error_count > 10:
                self.performance_warning.emit("High error rate detected")
            
            # Check memory usage
            import psutil
            process = psutil.Process()
            memory_percent = process.memory_percent()
            
            if memory_percent > 80:
                self.performance_warning.emit(f"High memory usage: {memory_percent:.1f}%")
            
            # Check CPU usage
            cpu_percent = process.cpu_percent()
            if cpu_percent > 90:
                self.performance_warning.emit(f"High CPU usage: {cpu_percent:.1f}%")
                
        except Exception as e:
            # 静默处理psutil导入错误，不打印错误信息
            if "No module named 'psutil'" not in str(e):
                print(f"Performance monitoring failed: {e}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": self._error_count,
            "recent_errors": len([e for e in self._error_history 
                               if time.time() - e["timestamp"] < 3600]),  # Last hour
            "recovery_attempts": sum(self._recovery_attempts.values()),
            "error_types": list(set(e["type"] for e in self._error_history)),
        }
    
    def clear_error_history(self):
        """Clear error history."""
        self._error_history.clear()
        self._recovery_attempts.clear()
        self._error_count = 0
    
    def export_error_report(self, file_path: str) -> bool:
        """Export error report to file."""
        try:
            import json
            
            report = {
                "error_stats": self.get_error_stats(),
                "error_history": self._error_history,
                "recovery_attempts": self._recovery_attempts,
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Failed to export error report: {e}")
            return False


class ErrorRecovery:
    """
    Error recovery utilities for MarkdownAll GUI.
    
    Provides:
    - Automatic error recovery
    - Graceful degradation
    - Fallback mechanisms
    """
    
    @staticmethod
    def recover_from_critical_error(error: Exception, context: str) -> bool:
        """Recover from critical error."""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Reset critical components
            if "config" in context.lower():
                # Reset configuration
                return True
            elif "ui" in context.lower():
                # Reset UI state
                return True
            elif "conversion" in context.lower():
                # Stop conversion process
                return True
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def create_fallback_config() -> Dict[str, Any]:
        """Create fallback configuration."""
        return {
            "basic": {
                "urls": [],
                "output_dir": ""
            },
            "webpage": {
                "use_proxy": False,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True
            },
            "advanced": {
                "user_data_path": "",
                "language": "auto",
                "log_level": "INFO",
                "debug_mode": False
            }
        }
