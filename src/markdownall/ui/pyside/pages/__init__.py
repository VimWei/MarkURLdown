"""
Pages module for MarkdownAll GUI.

This module contains all the page components for the tabbed interface:
- BasicPage: URL management and output directory configuration
- WebpagePage: Conversion options configuration
- AdvancedPage: Advanced options and system management
- AboutPage: Project homepage and version check
"""

from .about_page import AboutPage
from .advanced_page import AdvancedPage
from .basic_page import BasicPage
from .webpage_page import WebpagePage

__all__ = [
    "BasicPage",
    "WebpagePage",
    "AdvancedPage",
    "AboutPage",
]
