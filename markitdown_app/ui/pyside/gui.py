from __future__ import annotations

import os
from typing import Callable

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QCheckBox,
    QProgressBar, QFileDialog, QMessageBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QIcon

from markitdown_app.types import SourceRequest, ConversionOptions, ProgressEvent
from markitdown_app.ui.viewmodel import ViewModel
from markitdown_app.io.config import load_config, save_config, load_json_from_root


class ProgressSignals(QObject):
    """用于跨线程发送进度信号的辅助类"""
    progress_event = Signal(object)  # ProgressEvent


class PySideApp(QMainWindow):
    def __init__(self, root_dir: str, settings: dict | None = None):
        super().__init__()

        # -- Persisted, app-level settings --
        settings = settings or {}
        self.root_dir = root_dir
        # (Future: self.language = settings.get('language', 'en'))

        # -- Session state (starts with clean defaults) --
        self.url_var = ""
        default_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "output")
        self.output_dir_var = os.path.abspath(default_output_dir)
        self.status_var = "准备就绪"
        self.detail_var = ""
        self.is_running = False

        # Default options
        self.ignore_ssl_var = False
        self.no_proxy_var = True
        self.download_images_var = False

        # -- Component Initialization --
        self.vm = ViewModel()
        self.signals = ProgressSignals()
        
        self._setup_ui()
        self._connect_signals()

    def closeEvent(self, event):
        """在窗口关闭时自动保存当前会话状态"""
        try:
            state_data = {
                "urls": [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())],
                "output_dir": self.output_entry.text(),
                "ignore_ssl": self.ignore_ssl_cb.isChecked(),
                "no_proxy": self.no_proxy_cb.isChecked(),
                "download_images": self.download_images_cb.isChecked(),
            }
            
            state_path = os.path.join(self.root_dir, "last_state.json")
            save_config(state_path, state_data)
            
        except Exception as e:
            print(f"Error saving session state on exit: {e}")
        finally:
            event.accept()

    def _setup_ui(self):
        self.setWindowTitle("MarkURLdown (URL → Markdown)")

        # --- Set Application Icon ---
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'app_icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # --------------------------
        self.resize(920, 560)
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.setMinimumSize(800, 480)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QGridLayout(central_widget)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(6)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("网页 URL"), 0, 0)
        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.url_entry, 0, 1)

        button_height = self.url_entry.sizeHint().height()

        self.add_btn = QPushButton("添加 +")
        self.add_btn.setFixedHeight(button_height)
        layout.addWidget(self.add_btn, 0, 2)

        layout.addWidget(QLabel("URL 列表"), 1, 0)
        self.url_listbox = QListWidget()
        layout.addWidget(self.url_listbox, 1, 1)

        url_btn_frame = QFrame()
        url_btn_layout = QVBoxLayout(url_btn_frame)
        url_btn_layout.setSpacing(2)
        url_btn_layout.setContentsMargins(0, 0, 0, 0)

        self.move_up_btn = QPushButton("上移 ↑")
        self.move_down_btn = QPushButton("下移 ↓")
        self.delete_btn = QPushButton("删除 ✕")
        self.clear_btn = QPushButton("清空")

        for btn in [self.move_up_btn, self.move_down_btn, self.delete_btn, self.clear_btn]:
            btn.setFixedHeight(button_height)
            url_btn_layout.addWidget(btn)

        layout.addWidget(url_btn_frame, 1, 2)

        layout.addWidget(QLabel("输出目录"), 2, 0)
        self.output_entry = QLineEdit(self.output_dir_var)
        self.output_entry.setStyleSheet("QLineEdit { padding: 4px; }")
        layout.addWidget(self.output_entry, 2, 1)
        self.choose_dir_btn = QPushButton("选择…")
        self.choose_dir_btn.setFixedHeight(button_height)
        layout.addWidget(self.choose_dir_btn, 2, 2)

        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setSpacing(20)
        options_layout.setContentsMargins(0, 8, 0, 8)
        options_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.no_proxy_cb = QCheckBox("禁用系统代理")
        self.no_proxy_cb.setChecked(self.no_proxy_var)
        self.ignore_ssl_cb = QCheckBox("忽略 SSL 验证 (不安全)")
        self.ignore_ssl_cb.setChecked(self.ignore_ssl_var)
        self.download_images_cb = QCheckBox("下载图片（速度慢）")
        self.download_images_cb.setChecked(self.download_images_var)

        for cb in [self.no_proxy_cb, self.ignore_ssl_cb, self.download_images_cb]:
            options_layout.addWidget(cb)

        layout.addWidget(options_frame, 3, 0, 1, 3)

        import_export_frame = QFrame()
        import_export_layout = QHBoxLayout(import_export_frame)
        import_export_layout.setSpacing(6)
        import_export_layout.setContentsMargins(0, 0, 0, 0)
        import_export_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.restore_btn = QPushButton("恢复上次会话")
        self.export_btn = QPushButton("导出配置")
        self.import_btn = QPushButton("导入配置")

        for btn in [self.restore_btn, self.export_btn, self.import_btn]:
            btn.setFixedSize(120, 32)
            import_export_layout.addWidget(btn)

        layout.addWidget(import_export_frame, 4, 0, 1, 3)

        convert_frame = QFrame()
        convert_layout = QHBoxLayout(convert_frame)
        convert_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.convert_btn = QPushButton("转换为 Markdown")
        self.convert_btn.setFont(QFont("", 11, QFont.Weight.Bold))
        self.convert_btn.setFixedSize(200, 40)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        convert_layout.addWidget(self.convert_btn)
        layout.addWidget(convert_frame, 5, 0, 1, 3)

        self.progress = QProgressBar()
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 2px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 1px;
            }
        """)

        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 4, 0, 4)
        progress_layout.addWidget(self.progress)
        layout.addWidget(progress_frame, 6, 0, 1, 3)

        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(2)
        status_layout.setContentsMargins(0, 4, 0, 0)

        self.status_label = QLabel(self.status_var)
        self.status_label.setStyleSheet("color: #555; font-size: 10pt;")

        self.detail_label = QLabel(self.detail_var)
        self.detail_label.setStyleSheet("color: #777; font-size: 9pt;")

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        layout.addWidget(status_frame, 7, 0, 1, 3)

        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)

        self.url_entry.setFocus()

    def _connect_signals(self):
        self.add_btn.clicked.connect(self._add_url_from_entry)
        self.move_up_btn.clicked.connect(self._move_selected_up)
        self.move_down_btn.clicked.connect(self._move_selected_down)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_btn.clicked.connect(self._clear_list)
        self.choose_dir_btn.clicked.connect(self._choose_output_dir)
        
        self.restore_btn.clicked.connect(self._restore_last_session)
        self.export_btn.clicked.connect(self._export_config)
        self.import_btn.clicked.connect(self._import_config)
        
        self.convert_btn.clicked.connect(self._on_convert)
        self.signals.progress_event.connect(self._on_event)
        self.url_entry.returnPressed.connect(self._add_url_from_entry)

    def _restore_last_session(self):
        """加载并应用 last_state.json"""
        try:
            state = load_json_from_root(self.root_dir, "last_state.json")
            if not state:
                self.status_label.setText("没有找到上次的会话状态")
                return

            self._apply_state(state)
            self.status_label.setText("已成功恢复上次的会话")
        except Exception as e:
            self.status_label.setText("恢复会话失败")
            self.detail_label.setText(str(e))
            QMessageBox.critical(self, "错误", f"恢复上次会话失败:\n{e}")

    def _apply_state(self, state: dict):
        """将一个状态字典应用到UI上"""
        self.url_listbox.clear()
        for url in state.get("urls", []):
            self.url_listbox.addItem(url)

        if "output_dir" in state:
            self.output_entry.setText(state["output_dir"])
        if "ignore_ssl" in state:
            self.ignore_ssl_cb.setChecked(bool(state["ignore_ssl"]))
        if "no_proxy" in state:
            self.no_proxy_cb.setChecked(bool(state["no_proxy"]))
        if "download_images" in state:
            self.download_images_cb.setChecked(bool(state["download_images"]))

    def _choose_output_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "选择输出目录",
            self.output_entry.text() or os.getcwd()
        )
        if chosen:
            self.output_entry.setText(os.path.abspath(chosen))

    def _on_convert(self):
        if self.is_running:
            self._stop()
            return

        urls = []
        for i in range(self.url_listbox.count()):
            urls.append(self.url_listbox.item(i).text())

        if not urls:
            url = self.url_entry.text().strip()
            if not url:
                return
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            urls = [url]

        out_dir = self.output_entry.text().strip() or os.getcwd()
        self.is_running = True
        self.convert_btn.setText("停止转换")
        self.progress.setVisible(True)
        self.progress.setRange(0, len(urls))
        self.progress.setValue(0)
        self.status_label.setText("正在转换…")
        self.detail_label.setText("")

        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(
            ignore_ssl=self.ignore_ssl_cb.isChecked(),
            no_proxy=self.no_proxy_cb.isChecked(),
            download_images=self.download_images_cb.isChecked(),
        )
        self.vm.start(reqs, out_dir, options, self._on_event)

    def _stop(self):
        self.vm.stop(self._on_event)

    def _on_event(self, ev: ProgressEvent):
        if ev.kind == "progress_init":
            self.progress.setRange(0, max(ev.total or 1, 1))
            self.progress.setValue(0)
            if ev.text:
                self.status_label.setText(ev.text)
        elif ev.kind == "status":
            if ev.text:
                self.status_label.setText(ev.text)
        elif ev.kind == "detail":
            if ev.text:
                self.detail_label.setText(ev.text)
        elif ev.kind == "progress_step":
            current = self.progress.value()
            self.progress.setValue(current + 1)
            if ev.text:
                self.detail_label.setText(ev.text)
        elif ev.kind == "progress_done":
            self.progress.setValue(self.progress.maximum())
            if ev.text:
                self.status_label.setText(ev.text)
            self.is_running = False
            self.convert_btn.setText("转换为 Markdown")
        elif ev.kind == "stopped":
            self.status_label.setText(ev.text or "已停止")
            self.is_running = False
            self.convert_btn.setText("转换为 Markdown")
        elif ev.kind == "error":
            self.detail_label.setText(ev.text or "错误")
            self.is_running = False
            self.convert_btn.setText("转换为 Markdown")

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

    def _export_config(self):
        try:
            data = {
                "urls": [self.url_listbox.item(i).text() for i in range(self.url_listbox.count())],
                "output_dir": self.output_entry.text(),
                "ignore_ssl": self.ignore_ssl_cb.isChecked(),
                "no_proxy": self.no_proxy_cb.isChecked(),
                "download_images": self.download_images_cb.isChecked(),
            }

            filename, _ = QFileDialog.getSaveFileName(
                self, "导出配置", "", "JSON files (*.json);;All files (*.*)"
            )

            if filename:
                save_config(filename, data)
                self.status_label.setText(f"配置已导出到: {os.path.basename(filename)}")
                self.detail_label.setText(f"完整路径: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出配置失败:\n{e}")

    def _import_config(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "导入配置", "", "JSON files (*.json);;All files (*.*)"
            )

            if filename:
                config = load_config(filename)
                self._apply_state(config) # Use the new helper function
                self.status_label.setText(f"配置已从 {os.path.basename(filename)} 导入")
                self.detail_label.setText(f"导入了 {len(config.get('urls', []))} 个URL")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入配置失败:\n{e}")
