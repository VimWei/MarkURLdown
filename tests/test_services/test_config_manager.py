"""Test ConfigManager functionality."""

import json
import os
import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest

from markdownall.config.config_manager import ConfigManager
from markdownall.config.config_models import (
    AboutConfig,
    AdvancedConfig,
    BasicConfig,
    WebpageConfig,
)


class TestConfigManager:
    """Test ConfigManager class."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mark_changed(self):
        """Test mark_changed method."""
        # Test with auto_save disabled first
        self.config_manager._auto_save = False
        self.config_manager.mark_changed("basic")
        assert "basic" in self.config_manager._changed

        # Test marking multiple config types as changed
        self.config_manager.mark_changed("webpage")
        self.config_manager.mark_changed("advanced")
        assert "webpage" in self.config_manager._changed
        assert "advanced" in self.config_manager._changed

        # Test with auto_save enabled (will clear _changed after save)
        self.config_manager._auto_save = True
        self.config_manager._changed.clear()
        with patch.object(self.config_manager, "save_session") as mock_save:
            self.config_manager.mark_changed("about")
            assert "about" in self.config_manager._changed
            mock_save.assert_called_once()

    def test_has_changes(self):
        """Test has_changes method."""
        # Initially no changes
        assert not self.config_manager.has_changes()

        # After marking changes (with auto_save disabled)
        self.config_manager._auto_save = False
        self.config_manager.mark_changed("basic")
        assert self.config_manager.has_changes()

        # After clearing changes
        self.config_manager._changed.clear()
        assert not self.config_manager.has_changes()

    def test_import_config_success(self):
        """Test import_config method with valid config."""
        config_data = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {"use_proxy": True, "ignore_ssl": False},
            "advanced": {"language": "en"},
            "about": {"version": "1.0.0"},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            result = self.config_manager.import_config("test_config.json")
            assert result is True

            # Verify config was set
            assert self.config_manager.basic.urls == ["https://example.com"]
            assert self.config_manager.webpage.use_proxy is True
            assert self.config_manager.advanced.language == "en"

    def test_import_config_file_not_found(self):
        """Test import_config method with file not found."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = self.config_manager.import_config("nonexistent.json")
            assert result is False

    def test_import_config_invalid_json(self):
        """Test import_config method with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = self.config_manager.import_config("invalid.json")
            assert result is False

    def test_import_config_exception_handling(self):
        """Test import_config method with exception during processing."""
        config_data = {"basic": {"urls": ["https://example.com"]}}

        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            with patch.object(
                self.config_manager, "set_all_config", side_effect=Exception("Test error")
            ):
                result = self.config_manager.import_config("test.json")
                assert result is False

    def test_load_session_success(self):
        """Test load_session method with valid session."""
        session_data = {
            "basic": {"urls": ["https://example.com"], "output_dir": "/tmp"},
            "webpage": {"use_proxy": True},
        }

        # Create session file
        session_path = os.path.join(self.config_manager.config_dir, "test_session.json")
        os.makedirs(self.config_manager.config_dir, exist_ok=True)

        with open(session_path, "w") as f:
            json.dump(session_data, f)

        with patch("markdownall.io.config.load_config", return_value=session_data):
            result = self.config_manager.load_session("test_session")
            assert result is True

    def test_load_session_file_not_found(self):
        """Test load_session method with file not found."""
        result = self.config_manager.load_session("nonexistent")
        assert result is False

    def test_load_session_legacy_format(self):
        """Test load_session method with legacy format."""
        legacy_data = {
            "urls": ["https://example.com"],
            "output_dir": "/tmp",
            "use_proxy": True,
            "ignore_ssl": False,
        }

        # Create session file
        session_path = os.path.join(self.config_manager.config_dir, "legacy.json")
        os.makedirs(self.config_manager.config_dir, exist_ok=True)

        with open(session_path, "w") as f:
            import json

            json.dump(legacy_data, f)

        with patch("markdownall.io.config.load_config", return_value=legacy_data):
            with patch("markdownall.io.config.resolve_project_path", return_value="/tmp"):
                result = self.config_manager.load_session("legacy")
                assert result is True
                assert self.config_manager.basic.urls == ["https://example.com"]
                assert self.config_manager.webpage.use_proxy is True

    def test_save_session_success(self):
        """Test save_session method writes a valid session file."""
        # Set some config data
        self.config_manager.basic.urls = ["https://example.com"]
        self.config_manager.basic.output_dir = "/tmp"
        self.config_manager.webpage.use_proxy = True

        # Ensure target directory exists to avoid early failure
        os.makedirs(self.config_manager.config_dir, exist_ok=True)

        # Do real save (no mocking of save_config to avoid binding-order issues)
        result = self.config_manager.save_session("test_session")
        assert result is True

        # Verify file is created and JSON contains expected keys
        session_path = os.path.join(self.config_manager.config_dir, "test_session.json")
        assert os.path.isfile(session_path)
        from markdownall.io.config import load_config

        data = load_config(session_path)
        assert "basic" in data and "webpage" in data and "advanced" in data
        assert data["basic"]["urls"] == ["https://example.com"]
        assert len(self.config_manager._changed) == 0

    def test_save_session_exception(self):
        """Test save_session method with exception."""
        with patch("markdownall.io.config.save_config", side_effect=Exception("Save error")):
            with patch("os.makedirs"):
                result = self.config_manager.save_session("test_session")
                assert result is False

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method."""
        # Modify some configs
        self.config_manager.basic.urls = ["https://example.com"]
        self.config_manager.webpage.use_proxy = True
        self.config_manager._changed.add("basic")

        # Reset to defaults
        self.config_manager.reset_to_defaults()

        # Verify reset
        assert isinstance(self.config_manager.basic, BasicConfig)
        assert isinstance(self.config_manager.webpage, WebpageConfig)
        assert isinstance(self.config_manager.advanced, AdvancedConfig)
        assert isinstance(self.config_manager.about, AboutConfig)
        assert len(self.config_manager._changed) == 0

    def test_export_config_success(self):
        """Test export_config method."""
        # Set some config data
        self.config_manager.basic.urls = ["https://example.com"]

        with patch("builtins.open", mock_open()) as mock_file:
            result = self.config_manager.export_config("test_export.json")
            assert result is True
            mock_file.assert_called_once_with("test_export.json", "w", encoding="utf-8")

    def test_export_config_exception(self):
        """Test export_config method with exception."""
        with patch("builtins.open", side_effect=Exception("Export error")):
            result = self.config_manager.export_config("test_export.json")
            assert result is False

    def test_get_all_config(self):
        """Test get_all_config method."""
        # Set some config data
        self.config_manager.basic.urls = ["https://example.com"]
        self.config_manager.basic.output_dir = "/tmp"
        self.config_manager.webpage.use_proxy = True
        self.config_manager.advanced.language = "en"

        config = self.config_manager.get_all_config()

        assert "basic" in config
        assert "webpage" in config
        assert "advanced" in config
        assert config["basic"]["urls"] == ["https://example.com"]
        assert config["webpage"]["use_proxy"] is True
        assert config["advanced"]["language"] == "en"

    def test_set_all_config(self):
        """Test set_all_config method."""
        config_data = {
            "basic": {"urls": ["https://test.com"], "output_dir": "/test"},
            "webpage": {"use_proxy": False, "ignore_ssl": True},
            "advanced": {"language": "zh"},
            "about": {"version": "2.0.0"},
        }

        self.config_manager.set_all_config(config_data)

        assert self.config_manager.basic.urls == ["https://test.com"]
        assert self.config_manager.basic.output_dir == "/test"
        assert self.config_manager.webpage.use_proxy is False
        assert self.config_manager.webpage.ignore_ssl is True
        assert self.config_manager.advanced.language == "zh"
        assert (
            self.config_manager.about.homepage_clicked == False
        )  # AboutConfig doesn't have version attribute

    def test_set_all_config_partial(self):
        """Test set_all_config method with partial config."""
        config_data = {"basic": {"urls": ["https://partial.com"]}, "webpage": {"use_proxy": True}}

        self.config_manager.set_all_config(config_data)

        assert self.config_manager.basic.urls == ["https://partial.com"]
        assert self.config_manager.webpage.use_proxy is True
        # Other configs should remain unchanged
        assert isinstance(self.config_manager.advanced, AdvancedConfig)
        assert isinstance(self.config_manager.about, AboutConfig)
