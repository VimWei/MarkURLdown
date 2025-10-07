"""
Configuration Manager for MarkdownAll.

This module provides centralized configuration management,
following proper layered architecture principles.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, Dict

from markdownall.io.config import load_config, save_config, resolve_project_path, to_project_relative_path
from .config_models import BasicConfig, WebpageConfig, AdvancedConfig, AboutConfig


class ConfigManager:
    """
    Centralized configuration manager for MarkdownAll.
    
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
            
            # Support full new-format or legacy flat format
            if any(k in data for k in ("basic", "webpage", "advanced", "about")):
                self.set_all_config(data)
                return True
            
            # Legacy flat
            if "urls" in data:
                self.basic.urls = data.get("urls", [])
            if "output_dir" in data:
                self.basic.output_dir = resolve_project_path(data.get("output_dir", ""), self.root_dir)
            for key in ("use_proxy", "ignore_ssl", "download_images", "filter_site_chrome", "use_shared_browser"):
                if key in data:
                    setattr(self.webpage, key, bool(data.get(key)))
            return True
            
        except Exception as e:
            print(f"Failed to load session {session_name}: {e}")
            return False
    
    def save_session(self, session_name: str = "last_state") -> bool:
        """Save current session configuration (now writes full new-format)."""
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            session_path = os.path.join(self.sessions_dir, f"{session_name}.json")
            data = self.get_all_config()
            # Normalize output_dir to project-relative for persistence
            data["basic"]["output_dir"] = to_project_relative_path(self.basic.output_dir, self.root_dir)
            save_config(session_path, data)
            self._changed.clear()
            return True
            
        except Exception as e:
            print(f"Failed to save session {session_name}: {e}")
            return False
    
    def load_settings(self) -> bool:
        """Backward-compatible: load settings from unified session file."""
        return self.load_session()
    
    def save_settings(self) -> bool:
        """Backward-compatible: persist settings into unified session file."""
        return self.save_session()
    
    def mark_changed(self, config_type: str):
        """Mark configuration as changed."""
        self._changed.add(config_type)
        
        if self._auto_save:
            self.save_session()
    
    def has_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return len(self._changed) > 0
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary (clean schema)."""
        return {
            "basic": {
                "urls": list(self.basic.urls or []),
                "output_dir": self.basic.output_dir,
            },
            "webpage": {
                "use_proxy": bool(self.webpage.use_proxy),
                "ignore_ssl": bool(self.webpage.ignore_ssl),
                "download_images": bool(self.webpage.download_images),
                "filter_site_chrome": bool(self.webpage.filter_site_chrome),
                "use_shared_browser": bool(self.webpage.use_shared_browser),
            },
            "advanced": {
                "language": self.advanced.language,
            },
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
