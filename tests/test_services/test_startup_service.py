"""Test StartupService and BackgroundTaskManager functionality."""

import os
import tempfile
from unittest.mock import Mock, patch, call

import pytest

from markdownall.services.startup_service import StartupService, BackgroundTaskManager


class TestStartupService:
    """Test StartupService class."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.startup_service = StartupService(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_initialization_task(self):
        """Test add_initialization_task method."""
        task_func = Mock()
        self.startup_service.add_initialization_task("test_task", task_func)
        
        assert len(self.startup_service._initialization_tasks) == 1
        assert self.startup_service._initialization_tasks[0] == ("test_task", task_func)

    def test_initialize_configuration_success(self):
        """Test initialize_configuration method with success."""
        with patch.object(self.startup_service.config_service, 'load_session', return_value=True) as mock_load_session:
            with patch.object(self.startup_service.config_service, 'load_settings', return_value=True) as mock_load_settings:
                result = self.startup_service.initialize_configuration()
                assert result is True
                mock_load_session.assert_called_once()
                mock_load_settings.assert_called_once()

    def test_initialize_configuration_session_failure(self):
        """Test initialize_configuration method with session load failure."""
        with patch.object(self.startup_service.config_service, 'load_session', return_value=False):
            with patch.object(self.startup_service.config_service, 'load_settings', return_value=True):
                result = self.startup_service.initialize_configuration()
                assert result is True  # Still returns True if settings load succeeds

    def test_initialize_configuration_settings_failure(self):
        """Test initialize_configuration method with settings load failure."""
        with patch.object(self.startup_service.config_service, 'load_session', return_value=True):
            with patch.object(self.startup_service.config_service, 'load_settings', return_value=False):
                result = self.startup_service.initialize_configuration()
                assert result is True  # Still returns True if session load succeeds

    def test_initialize_configuration_exception(self):
        """Test initialize_configuration method with exception."""
        with patch.object(self.startup_service.config_service, 'load_session', side_effect=Exception("Test error")):
            with patch('builtins.print') as mock_print:
                result = self.startup_service.initialize_configuration()
                assert result is False
                mock_print.assert_called_once()

    def test_load_application_settings_success(self):
        """Test load_application_settings method with success."""
        result = self.startup_service.load_application_settings()
        assert result is True

    def test_load_application_settings_exception(self):
        """Test load_application_settings method with exception."""
        with patch('builtins.print') as mock_print:
            # This should not raise an exception in normal flow, but let's test the exception handling
            with patch.object(self.startup_service, 'config_service', side_effect=Exception("Test error")):
                result = self.startup_service.load_application_settings()
                assert result is False
                mock_print.assert_called_once()

    def test_prepare_background_tasks(self):
        """Test prepare_background_tasks method."""
        task1 = Mock()
        task2 = Mock()
        self.startup_service.add_initialization_task("task1", task1)
        self.startup_service.add_initialization_task("task2", task2)
        
        tasks = self.startup_service.prepare_background_tasks()
        assert len(tasks) == 2
        assert tasks == [("task1", task1), ("task2", task2)]
        
        # Verify it returns a copy
        tasks.append(("task3", Mock()))
        assert len(self.startup_service._initialization_tasks) == 2

    def test_get_config_service(self):
        """Test get_config_service method."""
        config_service = self.startup_service.get_config_service()
        assert config_service is self.startup_service.config_service

    def test_is_initialization_ready_success(self):
        """Test is_initialization_ready method with success."""
        # Create required directories
        required_dirs = [
            os.path.join(self.temp_dir, "data"),
            os.path.join(self.temp_dir, "data", "sessions"),
            os.path.join(self.temp_dir, "data", "output"),
        ]
        
        for dir_path in required_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        result = self.startup_service.is_initialization_ready()
        assert result is True

    def test_is_initialization_ready_missing_dirs(self):
        """Test is_initialization_ready method with missing directories."""
        # Don't create any directories
        result = self.startup_service.is_initialization_ready()
        assert result is False

    def test_is_initialization_ready_partial_dirs(self):
        """Test is_initialization_ready method with partial directories."""
        # Create only some directories
        os.makedirs(os.path.join(self.temp_dir, "data"), exist_ok=True)
        # Don't create sessions and output directories
        
        result = self.startup_service.is_initialization_ready()
        assert result is False

    def test_is_initialization_ready_creation_failure(self):
        """Test is_initialization_ready method with directory creation failure."""
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            result = self.startup_service.is_initialization_ready()
            assert result is False


class TestBackgroundTaskManager:
    """Test BackgroundTaskManager class."""

    def setup_method(self):
        """Setup test environment."""
        self.task_manager = BackgroundTaskManager()

    def test_init(self):
        """Test BackgroundTaskManager initialization."""
        assert self.task_manager._tasks == []
        assert self.task_manager._current_task_index == 0

    def test_add_task(self):
        """Test add_task method."""
        task_func = Mock()
        self.task_manager.add_task("test_task", task_func, "arg1", "arg2", kwarg1="value1")
        
        assert len(self.task_manager._tasks) == 1
        task_name, func, args, kwargs = self.task_manager._tasks[0]
        assert task_name == "test_task"
        assert func == task_func
        assert args == ("arg1", "arg2")
        assert kwargs == {"kwarg1": "value1"}

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks."""
        task1 = Mock()
        task2 = Mock()
        
        self.task_manager.add_task("task1", task1)
        self.task_manager.add_task("task2", task2, "arg1")
        
        assert len(self.task_manager._tasks) == 2
        assert self.task_manager._tasks[0][0] == "task1"
        assert self.task_manager._tasks[1][0] == "task2"

    def test_execute_tasks_success(self):
        """Test execute_tasks method with success."""
        task1 = Mock()
        task2 = Mock()
        
        self.task_manager.add_task("task1", task1)
        self.task_manager.add_task("task2", task2)
        
        progress_callback = Mock()
        result = self.task_manager.execute_tasks(progress_callback)
        
        assert result is True
        task1.assert_called_once()
        task2.assert_called_once()
        
        # Verify progress callback was called
        assert progress_callback.call_count == 2
        progress_callback.assert_has_calls([
            call("Background: task1", 0),
            call("Background: task2", 50)
        ])

    def test_execute_tasks_no_callback(self):
        """Test execute_tasks method without progress callback."""
        task1 = Mock()
        self.task_manager.add_task("task1", task1)
        
        result = self.task_manager.execute_tasks()
        assert result is True
        task1.assert_called_once()

    def test_execute_tasks_exception(self):
        """Test execute_tasks method with exception."""
        task1 = Mock(side_effect=Exception("Task error"))
        self.task_manager.add_task("task1", task1)
        
        progress_callback = Mock()
        result = self.task_manager.execute_tasks(progress_callback)
        
        assert result is False
        task1.assert_called_once()
        progress_callback.assert_called_with("Background task failed: Task error", 0)

    def test_execute_tasks_exception_no_callback(self):
        """Test execute_tasks method with exception and no callback."""
        task1 = Mock(side_effect=Exception("Task error"))
        self.task_manager.add_task("task1", task1)
        
        result = self.task_manager.execute_tasks()
        assert result is False

    def test_execute_tasks_empty(self):
        """Test execute_tasks method with no tasks."""
        progress_callback = Mock()
        result = self.task_manager.execute_tasks(progress_callback)
        
        assert result is True
        progress_callback.assert_not_called()

    def test_get_task_count(self):
        """Test get_task_count method."""
        assert self.task_manager.get_task_count() == 0
        
        self.task_manager.add_task("task1", Mock())
        assert self.task_manager.get_task_count() == 1
        
        self.task_manager.add_task("task2", Mock())
        assert self.task_manager.get_task_count() == 2

    def test_clear_tasks(self):
        """Test clear_tasks method."""
        self.task_manager.add_task("task1", Mock())
        self.task_manager.add_task("task2", Mock())
        self.task_manager._current_task_index = 5
        
        assert self.task_manager.get_task_count() == 2
        assert self.task_manager._current_task_index == 5
        
        self.task_manager.clear_tasks()
        
        assert self.task_manager.get_task_count() == 0
        assert self.task_manager._current_task_index == 0

    def test_execute_tasks_with_sleep(self):
        """Test execute_tasks method includes sleep delay."""
        task1 = Mock()
        self.task_manager.add_task("task1", task1)
        
        with patch('time.sleep') as mock_sleep:
            result = self.task_manager.execute_tasks()
            
            assert result is True
            task1.assert_called_once()
            mock_sleep.assert_called_once_with(0.01)

    def test_execute_tasks_progress_calculation(self):
        """Test execute_tasks method progress calculation."""
        task1 = Mock()
        task2 = Mock()
        task3 = Mock()
        
        self.task_manager.add_task("task1", task1)
        self.task_manager.add_task("task2", task2)
        self.task_manager.add_task("task3", task3)
        
        progress_callback = Mock()
        result = self.task_manager.execute_tasks(progress_callback)
        
        assert result is True
        
        # Verify progress percentages
        expected_calls = [
            call("Background: task1", 0),    # 0/3 * 100 = 0
            call("Background: task2", 33),   # 1/3 * 100 = 33
            call("Background: task3", 66)    # 2/3 * 100 = 66
        ]
        progress_callback.assert_has_calls(expected_calls)
