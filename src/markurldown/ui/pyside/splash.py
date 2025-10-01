from __future__ import annotations

import random
from pathlib import Path
from typing import Tuple

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

try:
    import importlib.resources as resources
except Exception:  # pragma: no cover
    import importlib_resources as resources  # type: ignore


def _pick_splash_image() -> QPixmap:
    try:
        assets_pkg = "markurldown.ui.assets"
        base = resources.files(assets_pkg)
        candidates = [
            base / "splash_01.png",
            base / "splash_02.png",
            base / "splash_03.png",
        ]
        existing = [p for p in candidates if p.is_file()]
        if not existing:
            return QPixmap(480, 320)
        chosen = Path(random.choice(existing))
        return QPixmap(str(chosen))
    except Exception:
        return QPixmap(480, 320)


def show_immediate_splash() -> Tuple[QApplication, QSplashScreen]:
    app = QApplication.instance() or QApplication([])
    pixmap = _pick_splash_image()
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    return app, splash


