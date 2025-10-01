from __future__ import annotations

import os
from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox

# Reuse existing splash utilities
from markurldown.ui.pyside.splash import show_immediate_splash


def _emit_startup_progress(app: QApplication, splash, message: str) -> None:
    splash.showMessage(message, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, color=QColor("white"))
    app.processEvents()


def main() -> None:
    app, splash = show_immediate_splash()
    try:
        _emit_startup_progress(app, splash, "Loading settings…")
        # Import lightweight config helper first
        from markurldown.io.config import load_json_from_root  # noqa: WPS433

        root_dir = os.getcwd()
        sessions_dir = os.path.join(root_dir, "data", "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        settings = load_json_from_root(sessions_dir, "settings.json") or {}

        # Minimal i18n for splash messages based on saved language
        lang = str(settings.get("language", "en"))
        is_zh = lang.startswith("zh")
        msg_loading = "正在加载配置…" if is_zh else "Loading settings…"
        msg_init = "正在初始化界面…" if is_zh else "Initializing UI…"
        msg_start = "正在启动应用…" if is_zh else "Starting application…"

        _emit_startup_progress(app, splash, msg_init)
        # Delay heavy GUI import until after settings are read
        from markurldown.ui.pyside.gui import PySideApp  # noqa: WPS433

        window = PySideApp(root_dir=root_dir, settings=settings)
        _emit_startup_progress(app, splash, msg_start)
        window.show()
        splash.finish(window)
        app.exec()
    except Exception as e:
        # Fallback minimal app to display error
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "MarkURLdown", f"Failed to start: {e}")
        raise


if __name__ == "__main__":
    main()


