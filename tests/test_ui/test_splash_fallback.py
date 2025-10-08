from __future__ import annotations

import os
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.splash import show_immediate_splash


def test_splash_fallback_methods_execute():
    app = QApplication.instance() or QApplication([])
    with patch.dict(
        os.environ, {"QT_QPA_PLATFORM": "offscreen", "PYTEST_CURRENT_TEST": "1"}, clear=False
    ):
        app, splash = show_immediate_splash()
        # Fallback returns an object with show/isVisible/showMessage/finish/close
        splash.show()
        assert hasattr(splash, "isVisible") and splash.isVisible() in (True, False)
        splash.showMessage("msg")
        splash.finish(None)
        splash.close()
