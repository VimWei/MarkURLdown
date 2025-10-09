from __future__ import annotations

import os
from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox

# Reuse existing splash utilities
from markdownall.ui.pyside.splash import show_immediate_splash


def _emit_startup_progress(app: QApplication, splash, message: str) -> None:
    splash.showMessage(
        message,
        alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        color=QColor("white"),
    )
    app.processEvents()


def main() -> None:
    app, splash = show_immediate_splash()
    try:
        _emit_startup_progress(app, splash, "Loading settings…")

        root_dir = os.getcwd()
        config_dir = os.path.join(root_dir, "data", "config")
        os.makedirs(config_dir, exist_ok=True)

        # Read language via ConfigService from unified session file
        from markdownall.services.config_service import ConfigService  # noqa: WPS433

        cfg = ConfigService(root_dir)
        cfg.load_session("last_state")  # best-effort; ok if missing
        lang = str(cfg.get_advanced_config().get("language", "en"))
        is_zh = lang.startswith("zh")
        msg_loading = "正在加载配置…" if is_zh else "Loading settings…"
        msg_init = "正在初始化界面…" if is_zh else "Initializing UI…"
        msg_start = "正在启动应用…" if is_zh else "Starting application…"

        _emit_startup_progress(app, splash, msg_init)
        # Import the new refactored GUI
        from markdownall.ui.pyside.main_window import MainWindow  # noqa: WPS433

        window = MainWindow(root_dir=root_dir, settings={"language": lang})
        _emit_startup_progress(app, splash, msg_start)
        window.show()
        splash.finish(window)
        app.exec()
    except Exception as e:
        # Fallback minimal app to display error
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "MarkdownAll", f"Failed to start: {e}")
        raise


if __name__ == "__main__":
    main()
