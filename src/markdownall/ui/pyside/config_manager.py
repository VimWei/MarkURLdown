"""
Configuration Manager for MarkdownAll GUI.

This module provides centralized configuration management for the GUI,
optimizing state management and reducing memory usage.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from markdownall.io.config import load_config, save_config, resolve_project_path, to_project_relative_path


@dataclass
class BasicConfig:
    """Basic page configuration."""
    urls: list[str] = None
    output_dir: str = ""
    
    def __post_init__(self):
        if self.urls is None:
            self.urls = []


@dataclass
class WebpageConfig:
    """Webpage page configuration."""
    use_proxy: bool = False
    ignore_ssl: bool = False
    download_images: bool = True
    filter_site_chrome: bool = True
    use_shared_browser: bool = True


@dataclass
class AdvancedConfig:
    """Advanced page configuration."""
    user_data_path: str = ""
    language: str = "auto"
    log_level: str = "INFO"
    debug_mode: bool = False


@dataclass
class AboutConfig:
    """About page configuration."""
    homepage_clicked: bool = False
    last_update_check: Optional[str] = None


class ConfigManager:
    """
    Centralized configuration manager for MarkdownAll GUI.
    
    This class provides:
    - Centralized configuration storage
    - Optimized state management
    - Memory-efficient configuration handling
    - Automatic configuration persistence
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.sessions_dir = os.path.join(root_dir, "data", "sessions")
        
        # Initialize configurations
        self.basic = BasicConfig()
        self.webpage = WebpageConfig()
        self.advanced = AdvancedConfig()
        self.about = AboutConfig()
        
        # Configuration change tracking
        self._changed = set()
        self._auto_save = True
        
    def load_session(self, session_name: str = "last_state") -> bool:
        """Load session configuration."""
        try:
            session_path = os.path.join(self.sessions_dir, f"{session_name}.json")
            if not os.path.exists(session_path):
                return False
                
            data = load_config(session_path)
            if not data:
                return False
                
            # Load basic config
            if "urls" in data:
                self.basic.urls = data["urls"]
            if "output_dir" in data:
                self.basic.output_dir = resolve_project_path(data["output_dir"], self.root_dir)
                
            # Load webpage config
            if "use_proxy" in data:
                self.webpage.use_proxy = bool(data["use_proxy"])
            if "ignore_ssl" in data:
                self.webpage.ignore_ssl = bool(data["ignore_ssl"])
            if "download_images" in data:
                self.webpage.download_images = bool(data["download_images"])
            if "filter_site_chrome" in data:
                self.webpage.filter_site_chrome = bool(data["filter_site_chrome"])
            if "use_shared_browser" in data:
                self.webpage.use_shared_browser = bool(data["use_shared_browser"])
                
            return True
            
        except Exception as e:
            print(f"Failed to load session {session_name}: {e}")
            return False
    
    def save_session(self, session_name: str = "last_state") -> bool:
        """Save current session configuration."""
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            session_path = os.path.join(self.sessions_dir, f"{session_name}.json")
            
            data = {
                "urls": self.basic.urls,
                "output_dir": to_project_relative_path(self.basic.output_dir, self.root_dir),
                "use_proxy": self.webpage.use_proxy,
                "ignore_ssl": self.webpage.ignore_ssl,
                "download_images": self.webpage.download_images,
                "filter_site_chrome": self.webpage.filter_site_chrome,
                "use_shared_browser": self.webpage.use_shared_browser,
            }
            
            save_config(session_path, data)
            self._changed.clear()
            return True
            
        except Exception as e:
            print(f"Failed to save session {session_name}: {e}")
            return False
    
    def load_settings(self) -> bool:
        """Load application settings."""
        try:
            settings_path = os.path.join(self.sessions_dir, "settings.json")
            if not os.path.exists(settings_path):
                return False
                
            data = load_config(settings_path)
            if not data:
                return False
                
            # Load advanced settings
            if "language" in data:
                self.advanced.language = data["language"]
            if "log_level" in data:
                self.advanced.log_level = data["log_level"]
            if "debug_mode" in data:
                self.advanced.debug_mode = bool(data["debug_mode"])
                
            return True
            
        except Exception as e:
            print(f"Failed to load settings: {e}")
            return False
    
    def save_settings(self) -> bool:
        """Save application settings."""
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            settings_path = os.path.join(self.sessions_dir, "settings.json")
            
            data = {
                "language": self.advanced.language,
                "log_level": self.advanced.log_level,
                "debug_mode": self.advanced.debug_mode,
            }
            
            save_config(settings_path, data)
            return True
            
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False
    
    def mark_changed(self, config_type: str):
        """Mark configuration as changed."""
        self._changed.add(config_type)
        
        if self._auto_save:
            self.save_session()
    
    def has_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return len(self._changed) > 0
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return {
            "basic": asdict(self.basic),
            "webpage": asdict(self.webpage),
            "advanced": asdict(self.advanced),
            "about": asdict(self.about),
        }
    
    def set_all_config(self, config: Dict[str, Any]):
        """Set all configuration from dictionary."""
        if "basic" in config:
            for key, value in config["basic"].items():
                if hasattr(self.basic, key):
                    setattr(self.basic, key, value)
        
        if "webpage" in config:
            for key, value in config["webpage"].items():
                if hasattr(self.webpage, key):
                    setattr(self.webpage, key, value)
        
        if "advanced" in config:
            for key, value in config["advanced"].items():
                if hasattr(self.advanced, key):
                    setattr(self.advanced, key, value)
        
        if "about" in config:
            for key, value in config["about"].items():
                if hasattr(self.about, key):
                    setattr(self.about, key, value)
    
    def reset_to_defaults(self):
        """Reset all configurations to default values."""
        self.basic = BasicConfig()
        self.webpage = WebpageConfig()
        self.advanced = AdvancedConfig()
        self.about = AboutConfig()
        self._changed.clear()
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to file."""
        try:
            config = self.get_all_config()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to export config: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.set_all_config(config)
            return True
        except Exception as e:
            print(f"Failed to import config: {e}")
            return False
