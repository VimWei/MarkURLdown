"""
Startup Manager for MarkdownAll GUI.

This module provides optimized startup management, including:
- Lazy loading of components
- Memory optimization
- Fast startup sequence
- Background initialization
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional, Callable, Any
from PySide6.QtCore import QObject, QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication

from markdownall.services.config_service import ConfigService


class StartupManager(QObject):
    """
    Optimized startup manager for MarkdownAll GUI.
    
    Features:
    - Lazy loading of heavy components
    - Background initialization
    - Memory optimization
    - Fast startup sequence
    """
    
    # Signals
    startup_progress = Signal(str, int)  # message, percentage
    startup_complete = Signal()
    startup_error = Signal(str)
    
    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = root_dir
        self.config_manager = ConfigManager(root_dir)
        
        # Startup phases
        self._phases = [
            ("Initializing configuration", self._init_config),
            ("Loading settings", self._load_settings),
            ("Preparing UI components", self._prepare_ui),
            ("Optimizing memory", self._optimize_memory),
            ("Finalizing startup", self._finalize_startup),
        ]
        
        self._current_phase = 0
        self._startup_timer = QTimer()
        self._startup_timer.timeout.connect(self._process_startup_phase)
        
    def start_startup(self):
        """Start the optimized startup sequence."""
        self._current_phase = 0
        self._startup_timer.start(50)  # Process phases with 50ms intervals
        
    def _process_startup_phase(self):
        """Process the current startup phase."""
        if self._current_phase >= len(self._phases):
            self._startup_timer.stop()
            self.startup_complete.emit()
            return
            
        phase_name, phase_func = self._phases[self._current_phase]
        progress = int((self._current_phase / len(self._phases)) * 100)
        
        try:
            self.startup_progress.emit(phase_name, progress)
            phase_func()
            self._current_phase += 1
        except Exception as e:
            self._startup_timer.stop()
            self.startup_error.emit(f"Startup failed at {phase_name}: {e}")
    
    def _init_config(self):
        """Initialize configuration system."""
        # Load basic configuration
        self.config_manager.load_session()
        self.config_manager.load_settings()
        
    def _load_settings(self):
        """Load application settings."""
        # This is handled by config_manager.load_settings()
        pass
        
    def _prepare_ui(self):
        """Prepare UI components (lazy loading)."""
        # UI components will be loaded on demand
        pass
        
    def _optimize_memory(self):
        """Optimize memory usage."""
        # Force garbage collection
        import gc
        gc.collect()
        
        # Optimize Python memory
        if hasattr(sys, 'set_int_max_str_digits'):
            sys.set_int_max_str_digits(0)  # Disable integer string conversion limits
            
    def _finalize_startup(self):
        """Finalize startup sequence."""
        # Any final optimizations
        pass
    
    def get_config_manager(self) -> ConfigManager:
        """Get the configuration manager."""
        return self.config_manager
    
    def is_startup_complete(self) -> bool:
        """Check if startup is complete."""
        return self._current_phase >= len(self._phases)


class BackgroundInitializer(QThread):
    """
    Background thread for heavy initialization tasks.
    
    This thread handles:
    - Heavy component loading
    - File system operations
    - Network operations
    - Other time-consuming tasks
    """
    
    # Signals
    progress_updated = Signal(str, int)  # message, percentage
    initialization_complete = Signal()
    initialization_error = Signal(str)
    
    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = root_dir
        self._tasks = []
        
    def add_task(self, name: str, func: Callable, *args, **kwargs):
        """Add a background initialization task."""
        self._tasks.append((name, func, args, kwargs))
        
    def run(self):
        """Run background initialization tasks."""
        try:
            total_tasks = len(self._tasks)
            
            for i, (name, func, args, kwargs) in enumerate(self._tasks):
                progress = int((i / total_tasks) * 100)
                self.progress_updated.emit(f"Background: {name}", progress)
                
                # Execute task
                func(*args, **kwargs)
                
                # Small delay to prevent UI blocking
                self.msleep(10)
                
            self.initialization_complete.emit()
            
        except Exception as e:
            self.initialization_error.emit(f"Background initialization failed: {e}")


class MemoryOptimizer:
    """
    Memory optimization utilities for MarkdownAll GUI.
    
    Features:
    - Memory usage monitoring
    - Automatic garbage collection
    - Memory leak detection
    - Performance optimization
    """
    
    def __init__(self):
        self._memory_threshold = 100 * 1024 * 1024  # 100MB
        self._last_gc_time = time.time()
        self._gc_interval = 30  # 30 seconds
        
    def check_memory_usage(self) -> float:
        """Check current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback to basic memory check
            import gc
            return len(gc.get_objects()) * 0.001  # Rough estimate
    
    def optimize_memory(self):
        """Optimize memory usage."""
        import gc
        
        # Force garbage collection
        collected = gc.collect()
        
        # Check if we need more aggressive cleanup
        current_time = time.time()
        if current_time - self._last_gc_time > self._gc_interval:
            # More aggressive cleanup
            gc.set_threshold(100, 10, 10)  # More frequent collection
            gc.collect()
            gc.set_threshold(700, 10, 10)  # Reset to default
            self._last_gc_time = current_time
            
        return collected
    
    def should_optimize(self) -> bool:
        """Check if memory optimization is needed."""
        memory_usage = self.check_memory_usage()
        return memory_usage > self._memory_threshold / 1024 / 1024
    
    def get_memory_info(self) -> dict:
        """Get detailed memory information."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss": memory_info.rss / 1024 / 1024,  # MB
                "vms": memory_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent(),
                "available": psutil.virtual_memory().available / 1024 / 1024,  # MB
            }
        except ImportError:
            return {
                "rss": self.check_memory_usage(),
                "vms": 0,
                "percent": 0,
                "available": 0,
            }
