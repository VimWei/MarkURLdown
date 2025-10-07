"""
Configuration data models for MarkdownAll.

This module defines the data structures used for configuration management,
separated from the business logic for better maintainability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    # debug_mode removed


@dataclass
class AboutConfig:
    """About page configuration."""
    homepage_clicked: bool = False
    last_update_check: Optional[str] = None
