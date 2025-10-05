"""
Configuration Service for MarkdownAll.

This module provides a service layer for configuration management,
offering high-level APIs for UI components to interact with configuration.
"""

from __future__ import annotations

from typing import Any, Dict

from markdownall.config.config_manager import ConfigManager


class ConfigService:
    """
    Configuration service - provides high-level APIs for UI layer.
    
    This service encapsulates the ConfigManager and provides
    simplified interfaces for UI components to interact with configuration.
    """
    
    def __init__(self, root_dir: str):
        self.config_manager = ConfigManager(root_dir)
    
    def load_session(self, session_name: str = "last_state") -> bool:
        """Load session configuration."""
        return self.config_manager.load_session(session_name)
    
    def save_session(self, session_name: str = "last_state") -> bool:
        """Save session configuration."""
        return self.config_manager.save_session(session_name)
    
    def load_settings(self) -> bool:
        """Load application settings."""
        return self.config_manager.load_settings()
    
    def save_settings(self) -> bool:
        """Save application settings."""
        return self.config_manager.save_settings()
    
    def reset_to_defaults(self) -> None:
        """Reset all configurations to default values."""
        self.config_manager.reset_to_defaults()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return self.config_manager.get_all_config()
    
    def set_all_config(self, config: Dict[str, Any]) -> None:
        """Set all configuration from dictionary."""
        self.config_manager.set_all_config(config)
    
    def get_basic_config(self) -> Dict[str, Any]:
        """Get basic configuration."""
        return self.config_manager.get_all_config()["basic"]
    
    def set_basic_config(self, config: Dict[str, Any]) -> None:
        """Set basic configuration."""
        all_config = self.get_all_config()
        all_config["basic"] = config
        self.set_all_config(all_config)
    
    def get_webpage_config(self) -> Dict[str, Any]:
        """Get webpage configuration."""
        return self.config_manager.get_all_config()["webpage"]
    
    def set_webpage_config(self, config: Dict[str, Any]) -> None:
        """Set webpage configuration."""
        all_config = self.get_all_config()
        all_config["webpage"] = config
        self.set_all_config(all_config)
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration."""
        return self.config_manager.get_all_config()["advanced"]
    
    def set_advanced_config(self, config: Dict[str, Any]) -> None:
        """Set advanced configuration."""
        all_config = self.get_all_config()
        all_config["advanced"] = config
        self.set_all_config(all_config)
    
    def get_about_config(self) -> Dict[str, Any]:
        """Get about configuration."""
        return self.config_manager.get_all_config()["about"]
    
    def set_about_config(self, config: Dict[str, Any]) -> None:
        """Set about configuration."""
        all_config = self.get_all_config()
        all_config["about"] = config
        self.set_all_config(all_config)
    
    def mark_changed(self, config_type: str) -> None:
        """Mark configuration as changed."""
        self.config_manager.mark_changed(config_type)
    
    def has_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.config_manager.has_changes()
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to file."""
        return self.config_manager.export_config(file_path)
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from file."""
        return self.config_manager.import_config(file_path)
    
    # Convenience methods for direct access to config objects
    @property
    def basic(self):
        """Direct access to basic config object."""
        return self.config_manager.basic
    
    @property
    def webpage(self):
        """Direct access to webpage config object."""
        return self.config_manager.webpage
    
    @property
    def advanced(self):
        """Direct access to advanced config object."""
        return self.config_manager.advanced
    
    @property
    def about(self):
        """Direct access to about config object."""
        return self.config_manager.about
