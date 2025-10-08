"""Test MemoryOptimizer and MemoryMonitor functionality."""

import gc
import time
from unittest.mock import Mock, patch, call

import pytest

from markdownall.utils.memory_optimizer import MemoryOptimizer, MemoryMonitor


class TestMemoryOptimizer:
    """Test MemoryOptimizer class."""

    def setup_method(self):
        """Setup test environment."""
        self.optimizer = MemoryOptimizer(memory_threshold_mb=100, gc_interval_seconds=30)

    def test_init(self):
        """Test MemoryOptimizer initialization."""
        assert self.optimizer._memory_threshold == 100 * 1024 * 1024  # 100MB in bytes
        assert self.optimizer._gc_interval == 30
        # Allow small drift between constructor timestamp and now
        assert abs(self.optimizer._last_gc_time - time.time()) < 1.0

    def test_check_memory_usage_with_psutil(self):
        """Test check_memory_usage method with psutil available."""
        with patch('psutil.Process') as mock_process:
            mock_process_instance = Mock()
            mock_process_instance.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
            mock_process.return_value = mock_process_instance
            
            memory_usage = self.optimizer.check_memory_usage()
            assert memory_usage == 50.0

    def test_check_memory_usage_without_psutil(self):
        """Test check_memory_usage method without psutil."""
        with patch('psutil.Process', side_effect=ImportError("No module named 'psutil'")):
            with patch('gc.get_objects', return_value=[1, 2, 3, 4, 5]):
                memory_usage = self.optimizer.check_memory_usage()
                assert memory_usage == 0.005  # 5 * 0.001

    def test_optimize_memory_basic(self):
        """Test optimize_memory method basic functionality."""
        with patch('gc.collect', return_value=10) as mock_collect:
            collected = self.optimizer.optimize_memory()
            assert collected == 10
            mock_collect.assert_called_once()

    def test_optimize_memory_aggressive_cleanup(self):
        """Test optimize_memory method with aggressive cleanup."""
        # Set last GC time to be older than interval
        self.optimizer._last_gc_time = time.time() - 60  # 60 seconds ago
        
        with patch('gc.collect', return_value=5) as mock_collect:
            with patch('gc.get_threshold', return_value=(700, 10, 10)) as mock_get_threshold:
                with patch('gc.set_threshold') as mock_set_threshold:
                    collected = self.optimizer.optimize_memory()
                    
                    assert collected == 5
                    # Should call collect twice (basic + aggressive)
                    assert mock_collect.call_count == 2
                    # Should set more aggressive thresholds
                    mock_set_threshold.assert_has_calls([
                        call(100, 10, 10),  # More aggressive
                        call(700, 10, 10)   # Reset to original
                    ])

    def test_should_optimize_true(self):
        """Test should_optimize method returns True when needed."""
        with patch.object(self.optimizer, 'check_memory_usage', return_value=150.0):  # 150MB > 100MB threshold
            assert self.optimizer.should_optimize() is True

    def test_should_optimize_false(self):
        """Test should_optimize method returns False when not needed."""
        with patch.object(self.optimizer, 'check_memory_usage', return_value=50.0):  # 50MB < 100MB threshold
            assert self.optimizer.should_optimize() is False

    def test_get_memory_info_with_psutil(self):
        """Test get_memory_info method with psutil available."""
        with patch('psutil.Process') as mock_process:
            mock_process_instance = Mock()
            mock_process_instance.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
            mock_process_instance.memory_info.return_value.vms = 100 * 1024 * 1024  # 100MB
            mock_process.return_value = mock_process_instance
            
            with patch('psutil.virtual_memory') as mock_virtual:
                mock_virtual.return_value.total = 8 * 1024 * 1024 * 1024  # 8GB
                mock_virtual.return_value.available = 4 * 1024 * 1024 * 1024  # 4GB
                mock_virtual.return_value.percent = 50.0
                
                memory_info = self.optimizer.get_memory_info()
                
                assert memory_info["rss_mb"] == 50.0
                assert memory_info["vms_mb"] == 100.0
                assert memory_info["total_mb"] == 8192.0
                assert memory_info["available_mb"] == 4096.0
                assert memory_info["percent"] == 50.0

    def test_get_memory_info_without_psutil(self):
        """Test get_memory_info method without psutil."""
        with patch('psutil.Process', side_effect=ImportError("No module named 'psutil'")):
            memory_info = self.optimizer.get_memory_info()
            
            assert memory_info["rss_mb"] == 0.0
            assert memory_info["vms_mb"] == 0.0
            assert memory_info["total_mb"] == 0.0
            assert memory_info["available_mb"] == 0.0
            assert memory_info["percent"] == 0.0

    def test_optimize_python_settings(self):
        """Test optimize_python_settings method."""
        with patch('gc.set_threshold') as mock_set_threshold:
            self.optimizer.optimize_python_settings()
            mock_set_threshold.assert_called_once_with(100, 10, 10)

    def test_get_gc_stats(self):
        """Test get_gc_stats method."""
        with patch('gc.get_count', return_value=(100, 10, 5)) as mock_get_count:
            stats = self.optimizer.get_gc_stats()
            assert stats == {"collections": 100, "collected": 10, "uncollectable": 5}
            mock_get_count.assert_called_once()

    def test_force_cleanup(self):
        """Test force_cleanup method."""
        with patch('gc.collect', return_value=15) as mock_collect:
            with patch('gc.set_threshold') as mock_set_threshold:
                with patch('gc.get_threshold', return_value=(700, 10, 10)) as mock_get_threshold:
                    collected = self.optimizer.force_cleanup()
                    
                    assert collected == 15
                    mock_collect.assert_called_once()
                    mock_set_threshold.assert_has_calls([
                        call(100, 10, 10),  # Set aggressive
                        call(700, 10, 10)   # Reset original
                    ])


class TestMemoryMonitor:
    """Test MemoryMonitor class."""

    def setup_method(self):
        """Setup test environment."""
        self.monitor = MemoryMonitor(sample_interval=1.0, max_samples=10)

    def test_init(self):
        """Test MemoryMonitor initialization."""
        assert self.monitor.sample_interval == 1.0
        assert self.monitor.max_samples == 10
        assert len(self.monitor.samples) == 0
        assert self.monitor.last_sample_time == 0

    def test_should_sample_true(self):
        """Test should_sample method returns True when should sample."""
        self.monitor.last_sample_time = time.time() - 2.0  # 2 seconds ago
        
        assert self.monitor.should_sample() is True

    def test_should_sample_false(self):
        """Test should_sample method returns False when shouldn't sample."""
        self.monitor.last_sample_time = time.time() - 0.5  # 0.5 seconds ago
        
        assert self.monitor.should_sample() is False

    def test_take_sample_with_psutil(self):
        """Test take_sample method with psutil available."""
        with patch('psutil.Process') as mock_process:
            mock_process_instance = Mock()
            mock_process_instance.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
            mock_process_instance.cpu_percent.return_value = 25.0
            mock_process.return_value = mock_process_instance
            
            with patch('psutil.virtual_memory') as mock_virtual:
                mock_virtual.return_value.percent = 60.0
                
                sample = self.monitor.take_sample()
                
                assert sample["timestamp"] > 0
                assert sample["rss_mb"] == 50.0
                assert sample["cpu_percent"] == 25.0
                assert sample["system_memory_percent"] == 60.0
                assert len(self.monitor.samples) == 1

    def test_take_sample_without_psutil(self):
        """Test take_sample method without psutil."""
        with patch('psutil.Process', side_effect=ImportError("No module named 'psutil'")):
            sample = self.monitor.take_sample()
            
            assert sample["timestamp"] > 0
            assert sample["rss_mb"] == 0.0
            assert sample["cpu_percent"] == 0.0
            assert sample["system_memory_percent"] == 0.0
            assert len(self.monitor.samples) == 1

    def test_take_sample_max_samples_limit(self):
        """Test take_sample method respects max_samples limit."""
        # Fill up samples to max
        for i in range(12):  # More than max_samples
            self.monitor.samples.append({"timestamp": i, "rss_mb": i * 10})
        
        with patch('psutil.Process', side_effect=ImportError("No module named 'psutil'")):
            self.monitor.take_sample()
            
            assert len(self.monitor.samples) == 10  # Should be limited to max_samples

    def test_take_sample_exception(self):
        """Test take_sample method with exception."""
        with patch('psutil.Process', side_effect=Exception("Process error")):
            sample = self.monitor.take_sample()
            
            assert sample["timestamp"] > 0
            assert sample["rss_mb"] == 0.0
            assert sample["cpu_percent"] == 0.0
            assert sample["system_memory_percent"] == 0.0

    def test_get_memory_trend_increasing(self):
        """Test get_memory_trend method with increasing trend."""
        # Add samples with increasing memory usage
        current_time = time.time()
        for i in range(5):
            self.monitor.samples.append({
                "timestamp": current_time - (4 - i) * 60,  # 4, 3, 2, 1, 0 minutes ago
                "rss_mb": 50 + i * 10  # 50, 60, 70, 80, 90 MB
            })
        
        trend = self.monitor.get_memory_trend()
        
        assert trend["trend"] == "increasing"
        assert trend["rate_mb_per_minute"] > 0
        assert trend["current_mb"] == 90.0
        assert trend["average_mb"] == 70.0

    def test_get_memory_trend_decreasing(self):
        """Test get_memory_trend method with decreasing trend."""
        # Add samples with decreasing memory usage
        current_time = time.time()
        for i in range(5):
            self.monitor.samples.append({
                "timestamp": current_time - (4 - i) * 60,  # 4, 3, 2, 1, 0 minutes ago
                "rss_mb": 90 - i * 10  # 90, 80, 70, 60, 50 MB
            })
        
        trend = self.monitor.get_memory_trend()
        
        assert trend["trend"] == "decreasing"
        assert trend["rate_mb_per_minute"] < 0
        assert trend["current_mb"] == 50.0
        assert trend["average_mb"] == 70.0

    def test_get_memory_trend_stable(self):
        """Test get_memory_trend method with stable trend."""
        # Add samples with stable memory usage
        current_time = time.time()
        for i in range(5):
            self.monitor.samples.append({
                "timestamp": current_time - (4 - i) * 60,  # 4, 3, 2, 1, 0 minutes ago
                "rss_mb": 70.0  # All 70 MB
            })
        
        trend = self.monitor.get_memory_trend()
        
        assert trend["trend"] == "stable"
        assert abs(trend["rate_mb_per_minute"]) < 0.1  # Very small rate
        assert trend["current_mb"] == 70.0
        assert trend["average_mb"] == 70.0

    def test_get_memory_trend_insufficient_samples(self):
        """Test get_memory_trend method with insufficient samples."""
        # Add only 1 sample
        self.monitor.samples.append({
            "timestamp": time.time(),
            "rss_mb": 50.0
        })
        
        trend = self.monitor.get_memory_trend()
        
        assert trend["trend"] == "unknown"
        assert trend["rate_mb_per_minute"] == 0.0
        assert trend["current_mb"] == 50.0
        assert trend["average_mb"] == 50.0

    def test_detect_memory_leak_true(self):
        """Test detect_memory_leak method returns True for leak."""
        # Add samples showing memory leak (increasing trend)
        current_time = time.time()
        for i in range(10):
            self.monitor.samples.append({
                "timestamp": current_time - (9 - i) * 60,  # 9, 8, ..., 0 minutes ago
                "rss_mb": 50 + i * 5  # 50, 55, 60, ..., 95 MB
            })
        
        assert self.monitor.detect_memory_leak() is True

    def test_detect_memory_leak_false(self):
        """Test detect_memory_leak method returns False for no leak."""
        # Add samples showing stable memory usage
        current_time = time.time()
        for i in range(10):
            self.monitor.samples.append({
                "timestamp": current_time - (9 - i) * 60,  # 9, 8, ..., 0 minutes ago
                "rss_mb": 70.0  # All 70 MB
            })
        
        assert self.monitor.detect_memory_leak() is False

    def test_get_samples(self):
        """Test get_samples method."""
        # Add some samples
        self.monitor.samples = [{"timestamp": 1, "rss_mb": 50}, {"timestamp": 2, "rss_mb": 60}]
        
        samples = self.monitor.get_samples()
        assert samples == [{"timestamp": 1, "rss_mb": 50}, {"timestamp": 2, "rss_mb": 60}]

    def test_clear_samples(self):
        """Test clear_samples method."""
        # Add some samples
        self.monitor.samples = [{"timestamp": 1, "rss_mb": 50}, {"timestamp": 2, "rss_mb": 60}]
        self.monitor.last_sample_time = 12345
        
        self.monitor.clear_samples()
        
        assert len(self.monitor.samples) == 0
        assert self.monitor.last_sample_time == 0
