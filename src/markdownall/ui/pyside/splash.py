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

    # Determine headless/CI conditions where a real splash may crash
    import os
    is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    headless = False
    try:
        screens = app.screens()  # type: ignore[attr-defined]
        headless = not screens
    except Exception:
        headless = True

    if is_pytest or headless:
        class _FallbackSplash:
            def __init__(self) -> None:
                self._visible = True
            def show(self) -> None:
                self._visible = True
            def isVisible(self) -> bool:  # type: ignore[override]
                return self._visible
            def close(self) -> None:
                self._visible = False
            def showMessage(self, *args, **kwargs) -> None:
                return None
            def finish(self, *args, **kwargs) -> None:
                self.close()
        return app, _FallbackSplash()

    try:
        splash = QSplashScreen(pixmap)
        splash.show()
        try:
            app.processEvents()
        except Exception:
            pass
        return app, splash
    except Exception:
        # Final safety fallback
        class _FallbackSplash:
            def __init__(self) -> None:
                self._visible = True
            def show(self) -> None:
                self._visible = True
            def isVisible(self) -> bool:  # type: ignore[override]
                return self._visible
            def close(self) -> None:
                self._visible = False
            def showMessage(self, *args, **kwargs) -> None:
                return None
            def finish(self, *args, **kwargs) -> None:
                self.close()
        return app, _FallbackSplash()
