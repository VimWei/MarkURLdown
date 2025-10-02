from __future__ import annotations

import json
import locale
import os
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QClipboard, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from markurldown.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markurldown.io.config import (
    load_config,
    load_json_from_root,
    resolve_project_path,
    save_config,
    to_project_relative_path,
)
from markurldown.ui.pyside.splash import show_immediate_splash
from markurldown.ui.viewmodel import ViewModel
from markurldown.version import get_app_title


class Translator:
    def __init__(self, locales_dir: str):
        self.locales_dir = locales_dir
        self.translations = {}

    def load_language(self, lang_code: str):
        if lang_code == "auto":
            lang_code, _ = locale.getdefaultlocale()
            lang_code = lang_code.split("_")[0] if lang_code else "en"

        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")

        if not os.path.exists(file_path):
            lang_code = "en"
            file_path = os.path.join(self.locales_dir, "en.json")

        with open(file_path, "r", encoding="utf-8") as f:
            self.translations = json.load(f)
        self.language = lang_code

    def t(self, key: str, **kwargs) -> str:
        text = self.translations.get(key, key)
        return text.format(**kwargs)


class ProgressSignals(QObject):
    progress_event = Signal(object)

    def __init__(self):
        super().__init__()


class PySideApp(QMainWindow):
    def __init__(self, root_dir: str, settings: dict | None = None):
        super().__init__()

        settings = settings or {}
        self.root_dir = root_dir
        self.ui_ready = False

        locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        self.translator = Translator(locales_dir)
        self.current_lang = settings.get("language", "auto")
        self.translator.load_language(self.current_lang)

        # Default output under project_root/data/output
        self.output_dir_var = os.path.abspath(os.path.join(root_dir, "data", "output"))
        self.is_running = False

        # Default options
        self.use_proxy_var = False
        self.ignore_ssl_var = False
        self.download_images_var = True
        self.filter_site_chrome_var = True
        self.use_shared_browser_var = True

        self.vm = ViewModel()
        self.signals = ProgressSignals()

        self._setup_ui()
        self._retranslate_ui()
        self._connect_signals()

        # 连接信号槽，确保线程安全的UI更新
        self.signals.progress_event.connect(self._on_event_thread_safe)
        self.ui_ready = True

    def closeEvent(self, event):
        try:
            state_data = {
                "urls": [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())],
                "output_dir": to_project_relative_path(self.output_entry.text(), self.root_dir),
                "use_proxy": self.use_proxy_cb.isChecked(),
                "ignore_ssl": self.ignore_ssl_cb.isChecked(),
                "download_images": self.download_images_cb.isChecked(),
                "filter_site_chrome": self.filter_site_chrome_cb.isChecked(),
                "use_shared_browser": self.use_shared_browser_cb.isChecked(),
            }
            state_path = os.path.join(self.root_dir, "data", "sessions", "last_state.json")
            save_config(state_path, state_data)
        except Exception as e:
            print(f"Error saving session state on exit: {e}")
        finally:
            event.accept()

    def _setup_ui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(920, 600)
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.setMinimumSize(800, 520)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QGridLayout(central_widget)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        # Row 0: URL Input
        self.url_label = QLabel()
        layout.addWidget(self.url_label, 0, 0)
        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.url_entry, 0, 1, 1, 2)
        button_height = self.url_entry.sizeHint().height()
        self.add_btn = QPushButton()
        self.add_btn.setFixedHeight(button_height)
        layout.addWidget(self.add_btn, 0, 3)

        # Row 1: URL List
        self.url_list_label = QLabel()
        layout.addWidget(self.url_list_label, 1, 0)
        self.url_listbox = QListWidget()
        layout.addWidget(self.url_listbox, 1, 1, 1, 2)
        url_btn_frame = QFrame()
        url_btn_layout = QVBoxLayout(url_btn_frame)
        url_btn_layout.setSpacing(2)
        url_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.move_up_btn = QPushButton()
        self.move_down_btn = QPushButton()
        self.copy_btn = QPushButton()
        self.delete_btn = QPushButton()
        self.clear_btn = QPushButton()
        for btn in [
            self.move_up_btn,
            self.move_down_btn,
            self.copy_btn,
            self.delete_btn,
            self.clear_btn,
        ]:
            btn.setFixedHeight(button_height)
            url_btn_layout.addWidget(btn)
        layout.addWidget(url_btn_frame, 1, 3)

        # Row 2: Output Directory
        self.output_dir_label = QLabel()
        layout.addWidget(self.output_dir_label, 2, 0)
        self.output_entry = QLineEdit(self.output_dir_var)
        self.output_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.output_entry, 2, 1, 1, 2)
        self.choose_dir_btn = QPushButton()
        self.choose_dir_btn.setFixedHeight(button_height)
        layout.addWidget(self.choose_dir_btn, 2, 3)

        # Row 3: Options
        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setSpacing(20)
        options_layout.setContentsMargins(0, 8, 0, 8)
        options_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.use_proxy_cb = QCheckBox()
        self.use_proxy_cb.setChecked(self.use_proxy_var)
        self.ignore_ssl_cb = QCheckBox()
        self.ignore_ssl_cb.setChecked(self.ignore_ssl_var)
        self.download_images_cb = QCheckBox()
        self.download_images_cb.setChecked(self.download_images_var)
        self.filter_site_chrome_cb = QCheckBox()
        self.filter_site_chrome_cb.setChecked(self.filter_site_chrome_var)
        self.use_shared_browser_cb = QCheckBox(self.translator.t("use_shared_browser_checkbox"))
        self.use_shared_browser_cb.setChecked(self.use_shared_browser_var)
        for cb in [
            self.use_proxy_cb,
            self.ignore_ssl_cb,
            self.download_images_cb,
            self.filter_site_chrome_cb,
            self.use_shared_browser_cb,
        ]:
            options_layout.addWidget(cb)
        layout.addWidget(options_frame, 3, 0, 1, 4)

        # Row 4: Actions
        import_export_frame = QFrame()
        import_export_layout = QHBoxLayout(import_export_frame)
        import_export_layout.setSpacing(6)
        import_export_layout.setContentsMargins(0, 0, 0, 0)
        import_export_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.restore_btn = QPushButton()
        self.import_btn = QPushButton()
        self.export_btn = QPushButton()
        for btn in [self.restore_btn, self.import_btn, self.export_btn]:
            btn.setFixedSize(150, 32)
            import_export_layout.addWidget(btn)
        layout.addWidget(import_export_frame, 4, 0, 1, 4)

        # Row 5: Convert Button
        convert_frame = QFrame()
        convert_layout = QHBoxLayout(convert_frame)
        convert_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.convert_btn = QPushButton()
        self.convert_btn.setFont(QFont("", 11, QFont.Weight.Bold))
        self.convert_btn.setFixedSize(200, 40)
        self.convert_btn.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; border: none; border-radius: 4px; padding: 8px; }\n"
            "QPushButton:hover { background-color: #106ebe; }\n"
            "QPushButton:pressed { background-color: #005a9e; }"
        )
        convert_layout.addWidget(self.convert_btn)
        layout.addWidget(convert_frame, 5, 0, 1, 4)

        # Row 6: Progress Bar
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 4, 0, 4)
        self.progress = QProgressBar()
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)  # 初始化为百分比模式，实际转换时会重新设置
        self.progress.setValue(0)
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #ccc; border-radius: 2px; text-align: center; }\n"
            "QProgressBar::chunk { background-color: #0078d4; border-radius: 1px; }"
        )
        progress_layout.addWidget(self.progress)
        layout.addWidget(progress_frame, 6, 0, 1, 4)

        # Row 7: Bottom Bar (Status & Language)
        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.setContentsMargins(0, 0, 0, 0)
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(2)
        status_layout.setContentsMargins(0, 4, 0, 0)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #555; font-size: 10pt;")
        self.detail_label = QLabel()
        self.detail_label.setStyleSheet("color: #777; font-size: 9pt;")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        lang_frame = QFrame()
        lang_layout = QHBoxLayout(lang_frame)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("简体中文", "zh")
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combo)
        index = self.lang_combo.findData(self.translator.language)
        if index != -1:
            self.lang_combo.setCurrentIndex(index)
        bottom_bar_layout.addWidget(status_frame, 1)
        bottom_bar_layout.addWidget(lang_frame, 0)
        layout.addLayout(bottom_bar_layout, 7, 0, 1, 4)

        # Final layout stretching
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(1, 1)
        self.url_entry.setFocus()

    def _retranslate_ui(self):
        t = self.translator.t
        self.setWindowTitle(get_app_title())
        self.url_label.setText(t("url_label"))
        self.add_btn.setText(t("add_button"))
        self.url_list_label.setText(t("url_list_label"))
        self.move_up_btn.setText(t("move_up_button"))
        self.move_up_btn.setToolTip(t("tooltip_move_up"))
        self.move_down_btn.setText(t("move_down_button"))
        self.move_down_btn.setToolTip(t("tooltip_move_down"))
        self.delete_btn.setText(t("delete_button"))
        self.delete_btn.setToolTip(t("tooltip_delete"))
        self.clear_btn.setText(t("clear_button"))
        self.clear_btn.setToolTip(t("tooltip_clear"))
        self.copy_btn.setText(t("copy_button"))
        self.copy_btn.setToolTip(t("tooltip_copy"))
        self.output_dir_label.setText(t("output_dir_label"))
        self.choose_dir_btn.setText(t("choose_dir_button"))
        self.lang_label.setText(t("language_label_text"))
        self.use_proxy_cb.setText(t("use_proxy_checkbox"))
        self.ignore_ssl_cb.setText(t("ignore_ssl_checkbox"))
        self.download_images_cb.setText(t("download_images_checkbox"))
        self.filter_site_chrome_cb.setText(t("filter_site_chrome_checkbox"))
        self.restore_btn.setText(t("restore_button"))
        self.export_btn.setText(t("export_button"))
        self.import_btn.setText(t("import_button"))
        self.convert_btn.setText(t("convert_button"))
        self.status_label.setText(t("status_ready"))

    def _connect_signals(self):
        self.add_btn.clicked.connect(self._add_url_from_entry)
        self.move_up_btn.clicked.connect(self._move_selected_up)
        self.move_down_btn.clicked.connect(self._move_selected_down)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_btn.clicked.connect(self._clear_list)
        self.copy_btn.clicked.connect(self._copy_selected)
        self.choose_dir_btn.clicked.connect(self._choose_output_dir)
        self.restore_btn.clicked.connect(self._restore_last_session)
        self.export_btn.clicked.connect(self._export_session)
        self.import_btn.clicked.connect(self._import_session)
        self.convert_btn.clicked.connect(self._on_convert)
        self.signals.progress_event.connect(self._on_event)
        self.url_entry.returnPressed.connect(self._add_url_from_entry)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

    def _on_language_changed(self, index: int):
        if not self.ui_ready:
            return
        lang_code = self.lang_combo.itemData(index)
        if lang_code == self.translator.language:
            return

        # Load the new language FIRST to show the message in the new language
        self.translator.load_language(lang_code)
        self.status_label.setText(self.translator.t("status_restart_required"))

        # Save the setting
        settings_path = os.path.join(self.root_dir, "data", "sessions", "settings.json")
        settings_data = {"language": lang_code}
        save_config(settings_path, settings_data)

    def _restore_last_session(self):
        try:
            sessions_dir = os.path.join(self.root_dir, "data", "sessions")
            state = load_json_from_root(sessions_dir, "last_state.json")
            if not state:
                self.status_label.setText(self.translator.t("status_no_session"))
                return
            self._apply_state(state)
            self.status_label.setText(self.translator.t("status_session_restored"))
        except Exception as e:
            self.status_label.setText(self.translator.t("status_session_failed"))
            self.detail_label.setText(str(e))
            QMessageBox.critical(
                self,
                self.translator.t("dialog_error_title"),
                self.translator.t("dialog_restore_failed", error=e),
            )

    def _apply_state(self, state: dict):
        self.url_listbox.clear()
        for url in state.get("urls", []):
            self.url_listbox.addItem(url)
        if "output_dir" in state:
            resolved = resolve_project_path(state["output_dir"], self.root_dir)
            self.output_entry.setText(resolved)
        if "use_proxy" in state:
            self.use_proxy_cb.setChecked(bool(state["use_proxy"]))
        if "ignore_ssl" in state:
            self.ignore_ssl_cb.setChecked(bool(state["ignore_ssl"]))
        if "download_images" in state:
            self.download_images_cb.setChecked(bool(state["download_images"]))
        if "filter_site_chrome" in state:
            self.filter_site_chrome_cb.setChecked(bool(state["filter_site_chrome"]))
        if "use_shared_browser" in state:
            self.use_shared_browser_cb.setChecked(bool(state["use_shared_browser"]))

    def _choose_output_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self,
            self.translator.t("dialog_choose_output_dir"),
            self.output_entry.text() or os.getcwd(),
        )
        if chosen:
            self.output_entry.setText(os.path.abspath(chosen))

    def _on_convert(self):
        if self.is_running:
            self._stop()
            return
        urls = [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())]
        if not urls:
            url = self.url_entry.text().strip()
            if not url:
                return
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            urls = [url]
        out_dir = self.output_entry.text().strip() or os.getcwd()
        self.is_running = True
        self.convert_btn.setText(self.translator.t("stop_button"))
        self.progress.setVisible(True)
        self.progress.setRange(0, len(urls))
        self.progress.setValue(0)
        self.status_label.setText(self.translator.t("status_converting"))
        self.detail_label.setText("")
        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(
            use_proxy=self.use_proxy_cb.isChecked(),
            ignore_ssl=self.ignore_ssl_cb.isChecked(),
            download_images=self.download_images_cb.isChecked(),
            filter_site_chrome=self.filter_site_chrome_cb.isChecked(),
            use_shared_browser=self.use_shared_browser_cb.isChecked(),
        )
        self.vm.start(reqs, out_dir, options, self._on_event, self.signals)

    def _stop(self):
        self.vm.stop(self._on_event)

    def _on_event_thread_safe(self, ev: ProgressEvent):
        """线程安全的UI事件处理，通过信号槽机制调用"""
        try:
            self._on_event(ev)
        except Exception as e:
            print(f"Error in thread-safe UI event handler: {e}")
            import traceback

            traceback.print_exc()

    def _on_event(self, ev: ProgressEvent):
        """UI事件处理的核心逻辑"""
        try:
            t = self.translator.t

            # Generate message from key or use raw text
            message = ""
            if ev.key:
                message = t(ev.key, **(ev.data or {}))
            elif ev.text:
                message = ev.text

            if ev.kind == "progress_init":
                self.progress.setRange(0, max(ev.total or 1, 1))
                self.progress.setValue(0)
                if message:
                    self.status_label.setText(message)
            elif ev.kind == "status":
                if message:
                    self.status_label.setText(message)
            elif ev.kind == "detail":
                if message:
                    self.detail_label.setText(message)
            elif ev.kind == "progress_step":
                # 使用事件中的实际完成数量，而不是累加
                if ev.data and "completed" in ev.data:
                    self.progress.setValue(ev.data["completed"])
                else:
                    # 向后兼容：如果没有提供completed数据，则累加
                    current = self.progress.value()
                    self.progress.setValue(current + 1)
                if message:
                    self.detail_label.setText(message)
            elif ev.kind == "progress_done":
                self.progress.setValue(self.progress.maximum())
                self.status_label.setText(message or t("status_done"))
                self.is_running = False
                self.convert_btn.setText(t("convert_button"))
            elif ev.kind == "stopped":
                self.status_label.setText(message or t("status_stopped"))
                self.is_running = False
                self.convert_btn.setText(t("convert_button"))
            elif ev.kind == "error":
                self.detail_label.setText(message or t("status_error"))
                self.is_running = False
                self.convert_btn.setText(t("convert_button"))

            # 强制UI更新，确保绘制完成
            self.update()
            QApplication.processEvents()

        except Exception as e:
            print(f"Error in UI event handler: {e}")
            import traceback

            traceback.print_exc()

    def _add_url_from_entry(self):
        raw = self.url_entry.text().strip()
        if not raw:
            return
        parts = [p.strip() for p in raw.replace("\r", "\n").split("\n")]
        urls = []
        for part in parts:
            if not part:
                continue
            for token in part.split():
                u = token.strip()
                if not u:
                    continue
                if not u.lower().startswith(("http://", "https://")):
                    u = "https://" + u
                urls.append(u)
        if not urls:
            return
        for u in urls:
            self.url_listbox.addItem(u)
        self.url_entry.setText("")

    def _move_selected_up(self):
        current = self.url_listbox.currentRow()
        if current > 0:
            item = self.url_listbox.takeItem(current)
            self.url_listbox.insertItem(current - 1, item)
            self.url_listbox.setCurrentRow(current - 1)

    def _move_selected_down(self):
        current = self.url_listbox.currentRow()
        if current < self.url_listbox.count() - 1:
            item = self.url_listbox.takeItem(current)
            self.url_listbox.insertItem(current + 1, item)
            self.url_listbox.setCurrentRow(current + 1)

    def _delete_selected(self):
        current = self.url_listbox.currentRow()
        if current >= 0:
            self.url_listbox.takeItem(current)

    def _clear_list(self):
        self.url_listbox.clear()

    def _copy_selected(self):
        current = self.url_listbox.currentRow()
        if current >= 0:
            url = self.url_listbox.item(current).text()
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            self.status_label.setText(self.translator.t("status_url_copied"))
            self.detail_label.setText(self.translator.t("detail_copied_url", url=url))

    def _export_session(self):
        t = self.translator.t
        sessions_dir = os.path.join(self.root_dir, "data", "sessions")
        try:
            data = {
                "urls": [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())],
                "output_dir": to_project_relative_path(self.output_entry.text(), self.root_dir),
                "use_proxy": self.use_proxy_cb.isChecked(),
                "ignore_ssl": self.ignore_ssl_cb.isChecked(),
                "download_images": self.download_images_cb.isChecked(),
                "filter_site_chrome": self.filter_site_chrome_cb.isChecked(),
                "use_shared_browser": self.use_shared_browser_cb.isChecked(),
            }
            filename, _ = QFileDialog.getSaveFileName(
                self, t("dialog_export_config"), sessions_dir, t("file_filter_json")
            )
            if filename:
                save_config(filename, data)
                self.status_label.setText(
                    t("status_config_exported", filename=os.path.basename(filename))
                )
                self.detail_label.setText(t("detail_full_path", path=filename))
        except Exception as e:
            QMessageBox.critical(self, t("dialog_error_title"), t("dialog_export_failed", error=e))

    def _import_session(self):
        t = self.translator.t
        sessions_dir = os.path.join(self.root_dir, "data", "sessions")
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, t("dialog_import_config"), sessions_dir, t("file_filter_json")
            )
            if filename:
                config = load_config(filename)
                self._apply_state(config)
                self.status_label.setText(
                    t("status_config_imported", filename=os.path.basename(filename))
                )
                self.detail_label.setText(
                    t("detail_imported_count", count=len(config.get("urls", [])))
                )
        except Exception as e:
            QMessageBox.critical(self, t("dialog_error_title"), t("dialog_import_failed", error=e))


def run_gui() -> None:
    try:
        app, splash = show_immediate_splash()
        root_dir = os.getcwd()
        settings = (
            load_json_from_root(os.path.join(root_dir, "data", "sessions"), "settings.json") or {}
        )
        window = PySideApp(root_dir=root_dir, settings=settings)
        window.show()
        splash.finish(window)
        app.exec()
    except Exception as e:
        # Fallback minimal app to display error
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "MarkURLdown", f"Failed to start: {e}")
        raise
