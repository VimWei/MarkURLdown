"""
Memory Optimization Utilities for MarkdownAll.

This module provides memory optimization and monitoring capabilities:
- Memory usage monitoring
- Automatic garbage collection
- Memory leak detection
- Performance optimization
"""

from __future__ import annotations

import gc
import sys
import time
from typing import Dict, Optional


class MemoryOptimizer:
    """
    Memory optimization utilities for MarkdownAll.
    
    Features:
    - Memory usage monitoring
    - Automatic garbage collection
    - Memory leak detection
    - Performance optimization
    """
    
    def __init__(self, memory_threshold_mb: int = 100, gc_interval_seconds: int = 30):
        """
        Initialize the memory optimizer.
        
        Args:
            memory_threshold_mb: Memory threshold in MB for optimization
            gc_interval_seconds: Interval in seconds for garbage collection
        """
        self._memory_threshold = memory_threshold_mb * 1024 * 1024  # Convert to bytes
        self._last_gc_time = time.time()
        self._gc_interval = gc_interval_seconds
        
    def check_memory_usage(self) -> float:
        """
        Check current memory usage in MB.
        
        Returns:
            float: Memory usage in MB
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback to basic memory check
            return len(gc.get_objects()) * 0.001  # Rough estimate in MB
    
    def optimize_memory(self) -> int:
        """
        Optimize memory usage.
        
        Returns:
            int: Number of objects collected by garbage collection
        """
        # Force garbage collection
        collected = gc.collect()
        
        # Check if we need more aggressive cleanup
        current_time = time.time()
        if current_time - self._last_gc_time > self._gc_interval:
            # More aggressive cleanup
            old_thresholds = gc.get_threshold()
            gc.set_threshold(100, 10, 10)  # More frequent collection
            gc.collect()
            gc.set_threshold(*old_thresholds)  # Reset to original thresholds
            self._last_gc_time = current_time
            
        return collected
    
    def should_optimize(self) -> bool:
        """
        Check if memory optimization is needed.
        
        Returns:
            bool: True if optimization is needed, False otherwise
        """
        memory_usage_mb = self.check_memory_usage()
        return memory_usage_mb > (self._memory_threshold / 1024 / 1024)
    
    def get_memory_info(self) -> Dict[str, float]:
        """
        Get detailed memory information.
        
        Returns:
            Dict[str, float]: Memory information dictionary
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            virtual_memory = psutil.virtual_memory()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                "percent": process.memory_percent(),
                "available_mb": virtual_memory.available / 1024 / 1024,  # Available memory in MB
                "total_mb": virtual_memory.total / 1024 / 1024,  # Total memory in MB
                "used_mb": virtual_memory.used / 1024 / 1024,  # Used memory in MB
            }
        except ImportError:
            # Fallback when psutil is not available
            return {
                "rss_mb": self.check_memory_usage(),
                "vms_mb": 0.0,
                "percent": 0.0,
                "available_mb": 0.0,
                "total_mb": 0.0,
                "used_mb": 0.0,
            }
    
    def optimize_python_settings(self):
        """Optimize Python runtime settings for better memory usage."""
        # Disable integer string conversion limits if available
        if hasattr(sys, 'set_int_max_str_digits'):
            sys.set_int_max_str_digits(0)
    
    def get_gc_stats(self) -> Dict[str, int]:
        """
        Get garbage collection statistics.
        
        Returns:
            Dict[str, int]: GC statistics
        """
        return {
            "collections": gc.get_count(),
            "thresholds": gc.get_threshold(),
            "objects": len(gc.get_objects()),
        }
    
    def force_cleanup(self) -> int:
        """
        Force aggressive memory cleanup.
        
        Returns:
            int: Number of objects collected
        """
        # Multiple garbage collection passes
        total_collected = 0
        for _ in range(3):
            collected = gc.collect()
            total_collected += collected
            if collected == 0:
                break  # No more objects to collect
        
        return total_collected


class MemoryMonitor:
    """
    Memory usage monitor for tracking memory patterns.
    
    Features:
    - Memory usage tracking over time
    - Memory leak detection
    - Performance trend analysis
    """
    
    def __init__(self, sample_interval_seconds: int = 60, max_samples: int = 100):
        """
        Initialize the memory monitor.
        
        Args:
            sample_interval_seconds: Interval between memory samples
            max_samples: Maximum number of samples to keep
        """
        self._sample_interval = sample_interval_seconds
        self._max_samples = max_samples
        self._samples: List[Dict[str, float]] = []
        self._last_sample_time = 0
        self._optimizer = MemoryOptimizer()
        
    def should_sample(self) -> bool:
        """Check if it's time to take a memory sample."""
        current_time = time.time()
        return current_time - self._last_sample_time >= self._sample_interval
    
    def take_sample(self) -> Optional[Dict[str, float]]:
        """
        Take a memory usage sample.
        
        Returns:
            Optional[Dict[str, float]]: Memory sample data or None if not ready
        """
        if not self.should_sample():
            return None
            
        sample = self._optimizer.get_memory_info()
        sample["timestamp"] = time.time()
        
        self._samples.append(sample)
        self._last_sample_time = sample["timestamp"]
        
        # Keep only the most recent samples
        if len(self._samples) > self._max_samples:
            self._samples.pop(0)
            
        return sample
    
    def get_memory_trend(self) -> Dict[str, float]:
        """
        Analyze memory usage trend.
        
        Returns:
            Dict[str, float]: Trend analysis results
        """
        if len(self._samples) < 2:
            return {"trend": 0.0, "growth_rate": 0.0}
        
        recent_samples = self._samples[-10:]  # Last 10 samples
        if len(recent_samples) < 2:
            return {"trend": 0.0, "growth_rate": 0.0}
        
        # Calculate trend
        first_sample = recent_samples[0]
        last_sample = recent_samples[-1]
        
        time_diff = last_sample["timestamp"] - first_sample["timestamp"]
        memory_diff = last_sample["rss_mb"] - first_sample["rss_mb"]
        
        growth_rate = memory_diff / time_diff if time_diff > 0 else 0.0
        
        return {
            "trend": memory_diff,
            "growth_rate": growth_rate,
            "samples_count": len(recent_samples),
        }
    
    def detect_memory_leak(self, threshold_mb_per_minute: float = 1.0) -> bool:
        """
        Detect potential memory leaks.
        
        Args:
            threshold_mb_per_minute: Memory growth threshold in MB per minute
            
        Returns:
            bool: True if potential memory leak detected, False otherwise
        """
        trend = self.get_memory_trend()
        growth_rate_per_minute = trend["growth_rate"] * 60  # Convert to per minute
        
        return growth_rate_per_minute > threshold_mb_per_minute
    
    def get_samples(self) -> List[Dict[str, float]]:
        """Get all memory samples."""
        return self._samples.copy()
    
    def clear_samples(self):
        """Clear all memory samples."""
        self._samples.clear()
        self._last_sample_time = 0
