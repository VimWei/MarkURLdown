from __future__ import annotations

import random
from pathlib import Path
from typing import Tuple

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QStyleFactory

try:
    import importlib.resources as resources
except Exception:  # pragma: no cover
    import importlib_resources as resources  # type: ignore


def _pick_splash_image() -> QPixmap:
    try:
        assets_pkg = "markdownall.ui.assets"
        base = resources.files(assets_pkg)
        candidates = [
            base / "splash_01.webp",
            base / "splash_02.webp",
            base / "splash_03.webp",
        ]
        existing = [p for p in candidates if p.is_file()]
        if not existing:
            pm = QPixmap(600, 350)
            pm.fill(QColor("#0a2a5e"))
            return pm
        chosen = Path(random.choice(existing))
        return QPixmap(str(chosen))
    except Exception:
        pm = QPixmap(600, 350)
        pm.fill(QColor("#0a2a5e"))
        return pm


def show_immediate_splash() -> Tuple[QApplication, QSplashScreen]:
    app = QApplication.instance() or QApplication([])

    # 设置Fusion样式
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")

    pixmap = _pick_splash_image()
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    return app, splash
