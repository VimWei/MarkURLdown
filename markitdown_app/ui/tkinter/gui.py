from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from markitdown_app.types import SourceRequest, ConversionOptions, ProgressEvent
from markitdown_app.ui.viewmodel import ViewModel
from markitdown_app.io.config import load_config, save_config


class TkApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.vm = ViewModel()

        self.url_var = tk.StringVar()
        default_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "output")
        self.output_dir_var = tk.StringVar(value=os.path.abspath(default_output_dir))
        self.status_var = tk.StringVar(value="准备就绪")
        self.detail_var = tk.StringVar(value="")
        self.is_running = False
        # options
        self.ignore_ssl_var = tk.BooleanVar(value=False)
        self.no_proxy_var = tk.BooleanVar(value=True)
        self.download_images_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        label_pad = {"padx": (10, 8), "pady": 6}
        input_pad = {"padx": (0, 10), "pady": 6}

        frm = ttk.Frame(self.root)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="网页 URL").grid(row=0, column=0, sticky=tk.W, **label_pad)
        entry = ttk.Entry(frm, textvariable=self.url_var)
        entry.grid(row=0, column=1, sticky=tk.EW, **input_pad)
        ttk.Button(frm, text="添加 +", command=self._add_url_from_entry).grid(row=0, column=2, sticky=tk.W, **pad)
        entry.focus_set()

        # URL 列表与操作
        ttk.Label(frm, text="URL 列表").grid(row=1, column=0, sticky=tk.W, **label_pad)
        self.url_listbox = tk.Listbox(frm, height=6)
        self.url_listbox.grid(row=1, column=1, sticky=tk.NSEW, **input_pad)
        btns = ttk.Frame(frm)
        btns.grid(row=1, column=2, sticky=tk.N, **pad)
        ttk.Button(btns, text="上移 ↑", command=self._move_selected_up).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="下移 ↓", command=self._move_selected_down).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="删除 ✕", command=self._delete_selected).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="清空", command=self._clear_list).pack(fill=tk.X, pady=2)

        ttk.Label(frm, text="输出目录").grid(row=2, column=0, sticky=tk.W, **label_pad)
        out_entry = ttk.Entry(frm, textvariable=self.output_dir_var)
        out_entry.grid(row=2, column=1, sticky=tk.EW, **input_pad)
        ttk.Button(frm, text="选择…", command=self._choose_output_dir).grid(row=2, column=2, sticky=tk.W, **pad)

        # 选项
        opts = ttk.Frame(frm)
        opts.grid(row=3, column=0, columnspan=3, sticky=tk.W, **pad)
        ttk.Checkbutton(opts, text="禁用系统代理", variable=self.no_proxy_var).pack(side=tk.LEFT)
        ttk.Checkbutton(opts, text="忽略 SSL 验证 (不安全)", variable=self.ignore_ssl_var).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(opts, text="下载图片（速度慢）", variable=self.download_images_var).pack(side=tk.LEFT, padx=(12, 0))

        # 导出/导入配置
        import_export_frame = ttk.Frame(frm)
        import_export_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, **pad)
        ttk.Button(import_export_frame, text="导出配置", command=self._export_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_export_frame, text="导入配置", command=self._import_config).pack(side=tk.LEFT, padx=5)

        action_frame = ttk.Frame(frm)
        action_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, **pad)
        self.convert_btn = ttk.Button(action_frame, text="转换为 Markdown", command=self._on_convert, style="Accent.TButton")
        self.convert_btn.pack(expand=True, pady=6)

        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky=tk.EW, **pad)
        ttk.Label(frm, textvariable=self.status_var).grid(row=7, column=0, columnspan=3, sticky=tk.W, **pad)
        ttk.Label(frm, textvariable=self.detail_var).grid(row=8, column=0, columnspan=3, sticky=tk.W, **pad)

        frm.grid_columnconfigure(1, weight=1)
        frm.grid_rowconfigure(1, weight=1)

    def _choose_output_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get() or os.getcwd(), title="选择输出目录")
        if chosen:
            self.output_dir_var.set(os.path.abspath(chosen))

    def _on_convert(self) -> None:
        if self.is_running:
            self._stop()
            return

        # 收集 URL 列表；若为空，使用输入框内容
        urls = [self.url_listbox.get(i) for i in range(self.url_listbox.size())]
        if not urls:
            url = (self.url_var.get() or "").strip()
            if not url:
                return
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            urls = [url]

        out_dir = (self.output_dir_var.get() or "").strip() or os.getcwd()
        self.is_running = True
        self.convert_btn.configure(text="停止转换")
        self.progress.configure(mode="determinate", maximum=len(urls), value=0)
        self.status_var.set("正在转换…")
        self.detail_var.set("")

        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(
            ignore_ssl=bool(self.ignore_ssl_var.get()),
            no_proxy=bool(self.no_proxy_var.get()),
            download_images=bool(self.download_images_var.get()),
        )
        self.vm.start(reqs, out_dir, options, self._on_event)

    def _stop(self) -> None:
        self.vm.stop(self._on_event)

    def _on_event(self, ev: ProgressEvent) -> None:
        if ev.kind == "progress_init":
            self.progress.configure(mode="determinate", maximum=max(ev.total or 1, 1), value=0)
            if ev.text:
                self.status_var.set(ev.text)
        elif ev.kind == "status":
            if ev.text:
                self.status_var.set(ev.text)
        elif ev.kind == "detail":
            if ev.text:
                self.detail_var.set(ev.text)
        elif ev.kind == "progress_step":
            cur = float(self.progress["value"]) if str(self.progress.cget("mode")) == "determinate" else 0
            self.progress.configure(value=cur + 1)
            if ev.text:
                self.detail_var.set(ev.text)
        elif ev.kind == "progress_done":
            self.progress.configure(value=float(self.progress["maximum"]))
            if ev.text:
                self.status_var.set(ev.text)
            self.is_running = False
            self.convert_btn.configure(text="转换为 Markdown")
        elif ev.kind == "stopped":
            self.status_var.set(ev.text or "已停止")
            self.is_running = False
            self.convert_btn.configure(text="转换为 Markdown")
        elif ev.kind == "error":
            self.detail_var.set(ev.text or "错误")
            self.is_running = False
            self.convert_btn.configure(text="转换为 Markdown")

    # URL 列表操作
    def _add_url_from_entry(self) -> None:
        raw = (self.url_var.get() or "").strip()
        if not raw:
            return
        # 支持一次性粘贴多行/以空白分隔的多个URL
        parts = [p.strip() for p in raw.replace("\r", "\n").split("\n")]
        urls: list[str] = []
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
            self.url_listbox.insert(tk.END, u)
        # 清空输入框
        self.url_var.set("")

    def _move_selected_up(self) -> None:
        if not self.url_listbox.curselection():
            return
        idx = self.url_listbox.curselection()[0]
        if idx > 0:
            url = self.url_listbox.get(idx)
            self.url_listbox.delete(idx)
            self.url_listbox.insert(idx - 1, url)
            self.url_listbox.selection_set(idx - 1)

    def _move_selected_down(self) -> None:
        if not self.url_listbox.curselection():
            return
        idx = self.url_listbox.curselection()[0]
        if idx < self.url_listbox.size() - 1:
            url = self.url_listbox.get(idx)
            self.url_listbox.delete(idx)
            self.url_listbox.insert(idx + 1, url)
            self.url_listbox.selection_set(idx + 1)

    def _delete_selected(self) -> None:
        sel = list(self.url_listbox.curselection())
        for i in reversed(sel):
            self.url_listbox.delete(i)

    def _clear_list(self) -> None:
        self.url_listbox.delete(0, tk.END)

    # 配置导入/导出
    def _export_config(self) -> None:
        try:
            data = {
                "urls": list(self.url_listbox.get(0, tk.END)),
                "output_dir": self.output_dir_var.get(),
                "ignore_ssl": bool(self.ignore_ssl_var.get()),
                "no_proxy": bool(self.no_proxy_var.get()),
                "download_images": bool(self.download_images_var.get()),
            }
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="导出配置",
            )
            if filename:
                save_config(filename, data)
                self.status_var.set(f"配置已导出到: {os.path.basename(filename)}")
                self.detail_var.set(f"完整路径: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"导出配置失败:\n{e}")

    def _import_config(self) -> None:
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="导入配置",
            )
            if filename:
                config = load_config(filename)
                # URL 列表
                self.url_listbox.delete(0, tk.END)
                for url in config.get("urls", []):
                    self.url_listbox.insert(tk.END, url)
                # 其他配置
                if "output_dir" in config:
                    self.output_dir_var.set(config["output_dir"])
                if "ignore_ssl" in config:
                    self.ignore_ssl_var.set(bool(config["ignore_ssl"]))
                if "no_proxy" in config:
                    self.no_proxy_var.set(bool(config["no_proxy"]))
                if "download_images" in config:
                    self.download_images_var.set(bool(config["download_images"]))
                self.status_var.set(f"配置已从 {os.path.basename(filename)} 导入")
                self.detail_var.set(f"导入了 {len(config.get('urls', []))} 个URL，输出目录: {config.get('output_dir', '默认')}")
        except Exception as e:
            messagebox.showerror("错误", f"导入配置失败:\n{e}")


