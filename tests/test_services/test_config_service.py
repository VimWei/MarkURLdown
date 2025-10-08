"""Test ConfigService functionality."""

import json
import os
import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest

from markdownall.services.config_service import ConfigService


class TestConfigService:
    """Test ConfigService class."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_service = ConfigService(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_settings(self):
        """Test load_settings method."""
        with patch.object(
            self.config_service.config_manager, "load_settings", return_value=True
        ) as mock_load:
            result = self.config_service.load_settings()
            assert result is True
            mock_load.assert_called_once()

    def test_save_settings(self):
        """Test save_settings method."""
        with patch.object(
            self.config_service.config_manager, "save_settings", return_value=True
        ) as mock_save:
            result = self.config_service.save_settings()
            assert result is True
            mock_save.assert_called_once()

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method."""
        with patch.object(self.config_service.config_manager, "reset_to_defaults") as mock_reset:
            self.config_service.reset_to_defaults()
            mock_reset.assert_called_once()

    def test_get_basic_config(self):
        """Test get_basic_config method."""
        expected_config = {"urls": ["https://example.com"], "output_dir": "/tmp"}

        with patch.object(
            self.config_service.config_manager,
            "get_all_config",
            return_value={"basic": expected_config},
        ) as mock_get:
            result = self.config_service.get_basic_config()
            assert result == expected_config
            mock_get.assert_called_once()

    def test_get_webpage_config(self):
        """Test get_webpage_config method."""
        expected_config = {"use_proxy": True, "ignore_ssl": False}

        with patch.object(
            self.config_service.config_manager,
            "get_all_config",
            return_value={"webpage": expected_config},
        ) as mock_get:
            result = self.config_service.get_webpage_config()
            assert result == expected_config
            mock_get.assert_called_once()

    def test_get_about_config(self):
        """Test get_about_config method."""
        expected_config = {"version": "1.0.0", "author": "Test"}

        with patch.object(
            self.config_service.config_manager,
            "get_all_config",
            return_value={"about": expected_config},
        ) as mock_get:
            result = self.config_service.get_about_config()
            assert result == expected_config
            mock_get.assert_called_once()

    def test_set_about_config(self):
        """Test set_about_config method."""
        about_config = {"version": "2.0.0", "author": "Updated"}

        with patch.object(
            self.config_service.config_manager,
            "get_all_config",
            return_value={"basic": {}, "webpage": {}, "advanced": {}, "about": {}},
        ) as mock_get:
            with patch.object(self.config_service.config_manager, "set_all_config") as mock_set:
                self.config_service.set_about_config(about_config)

                # Verify get_all_config was called
                mock_get.assert_called_once()

                # Verify set_all_config was called with updated config
                call_args = mock_set.call_args[0][0]
                assert call_args["about"] == about_config

    def test_mark_changed(self):
        """Test mark_changed method."""
        with patch.object(self.config_service.config_manager, "mark_changed") as mock_mark:
            self.config_service.mark_changed("basic")
            mock_mark.assert_called_once_with("basic")

    def test_has_changes(self):
        """Test has_changes method."""
        with patch.object(
            self.config_service.config_manager, "has_changes", return_value=True
        ) as mock_has:
            result = self.config_service.has_changes()
            assert result is True
            mock_has.assert_called_once()

    def test_import_config_success(self):
        """Test import_config method with valid config."""
        config_data = {
            "basic": {"urls": ["https://example.com"]},
            "webpage": {"use_proxy": True},
            "advanced": {"language": "en"},
            "about": {"version": "1.0.0"},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            with patch.object(self.config_service.config_manager, "set_all_config") as mock_set:
                result = self.config_service.import_config("test_config.json")
                assert result is True
                mock_set.assert_called_once_with(config_data)

    def test_import_config_legacy_format(self):
        """Test import_config method with legacy format."""
        legacy_data = {
            "urls": ["https://example.com"],
            "output_dir": "/tmp",
            "use_proxy": True,
            "ignore_ssl": False,
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(legacy_data))):
            with patch("markdownall.io.config.resolve_project_path", return_value="/tmp"):
                result = self.config_service.import_config("legacy_config.json")
                assert result is True

                # Verify legacy config was applied
                assert self.config_service.config_manager.basic.urls == ["https://example.com"]
                assert self.config_service.config_manager.webpage.use_proxy is True

    def test_import_config_file_error(self):
        """Test import_config method with file error."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = self.config_service.import_config("nonexistent.json")
            assert result is False

    def test_import_config_invalid_data(self):
        """Test import_config method with invalid data."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = self.config_service.import_config("invalid.json")
            assert result is False

    def test_import_config_exception_during_processing(self):
        """Test import_config method with exception during processing."""
        config_data = {"basic": {"urls": ["https://example.com"]}}

        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            with patch.object(
                self.config_service.config_manager,
                "set_all_config",
                side_effect=Exception("Test error"),
            ):
                result = self.config_service.import_config("test.json")
                assert result is False

    def test_import_config_non_dict_data(self):
        """Test import_config method with non-dict data."""
        with patch("builtins.open", mock_open(read_data=json.dumps("not a dict"))):
            result = self.config_service.import_config("invalid.json")
            assert result is False

    def test_basic_property(self):
        """Test basic property access."""
        basic_config = self.config_service.basic
        assert basic_config is self.config_service.config_manager.basic

    def test_webpage_property(self):
        """Test webpage property access."""
        webpage_config = self.config_service.webpage
        assert webpage_config is self.config_service.config_manager.webpage

    def test_advanced_property(self):
        """Test advanced property access."""
        advanced_config = self.config_service.advanced
        assert advanced_config is self.config_service.config_manager.advanced

    def test_about_property(self):
        """Test about property access."""
        about_config = self.config_service.about
        assert about_config is self.config_service.config_manager.about

    def test_load_session(self):
        """Test load_session method."""
        with patch.object(
            self.config_service.config_manager, "load_session", return_value=True
        ) as mock_load:
            result = self.config_service.load_session("test_session")
            assert result is True
            mock_load.assert_called_once_with("test_session")

    def test_save_session(self):
        """Test save_session method."""
        with patch.object(
            self.config_service.config_manager, "save_session", return_value=True
        ) as mock_save:
            result = self.config_service.save_session("test_session")
            assert result is True
            mock_save.assert_called_once_with("test_session")

    def test_get_all_config(self):
        """Test get_all_config method."""
        expected_config = {"basic": {}, "webpage": {}, "advanced": {}, "about": {}}

        with patch.object(
            self.config_service.config_manager, "get_all_config", return_value=expected_config
        ) as mock_get:
            result = self.config_service.get_all_config()
            assert result == expected_config
            mock_get.assert_called_once()

    def test_set_all_config(self):
        """Test set_all_config method."""
        config_data = {"basic": {"urls": ["https://example.com"]}}

        with patch.object(self.config_service.config_manager, "set_all_config") as mock_set:
            self.config_service.set_all_config(config_data)
            mock_set.assert_called_once_with(config_data)

    def test_export_config(self):
        """Test export_config method."""
        with patch.object(
            self.config_service.config_manager, "export_config", return_value=True
        ) as mock_export:
            result = self.config_service.export_config("test_export.json")
            assert result is True
            mock_export.assert_called_once_with("test_export.json")
