"""
Theme Loader for MarkdownAll GUI.

This module loads and applies QSS styles to the application.
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtWidgets import QApplication


class ThemeLoader:
    """Loads and applies QSS themes to the application."""
    
    def __init__(self, theme_name: str = "default"):
        self.theme_name = theme_name
        self.theme_dir = Path(__file__).parent / "themes"
    
    def load_theme(self) -> str:
        """Load QSS theme content."""
        try:
            theme_file = self.theme_dir / f"{self.theme_name}.qss"
            if not theme_file.exists():
                # Fallback to default theme
                theme_file = self.theme_dir / "default.qss"
            if theme_file.exists():
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception:
                    # If reading fails, return empty content for safe no-op
                    return ""
            return ""
        except Exception:
            # On any unexpected error, return empty content
            return ""
    
    def apply_theme(self, app: QApplication):
        """Apply theme to the application."""
        try:
            qss_content = self.load_theme()
            if qss_content:
                app.setStyleSheet(qss_content)
        except Exception:
            # Swallow exceptions per tests; do not apply
            pass
    
    def apply_theme_to_widget(self, widget):
        """Apply theme to a specific widget."""
        try:
            qss_content = self.load_theme()
            if qss_content:
                widget.setStyleSheet(qss_content)
        except Exception:
            # Swallow exceptions per tests; do not apply
            pass
