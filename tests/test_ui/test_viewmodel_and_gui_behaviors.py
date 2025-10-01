from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from markurldown.app_types import ConversionOptions, ProgressEvent, SourceRequest
from markurldown.ui.pyside.gui import PySideApp
from markurldown.ui.viewmodel import ViewModel


@pytest.mark.unit
def test_viewmodel_delegates_to_service_run_and_stop():
    vm = ViewModel()
    with mock.patch.object(vm, "_service") as service_mock:
        dummy_event = object()
        vm.start(["req"], "out", mock.Mock(), mock.Mock())
        service_mock.run.assert_called_once()

        vm.stop(lambda _: None)
        service_mock.stop.assert_called_once()


def _make_window(tmp_path, qapp):
    root = tmp_path
    (root / "data" / "sessions").mkdir(parents=True)
    window = PySideApp(root_dir=str(root), settings={"language": "en"})
    return window


@pytest.mark.unit
def test_add_url_from_entry_normalizes_and_adds(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    window.url_entry.setText("example.com  https://already.com\n http://plain.net")
    window._add_url_from_entry()
    items = [window.url_listbox.item(i).text() for i in range(window.url_listbox.count())]
    assert items == [
        "https://example.com",
        "https://already.com",
        "http://plain.net",
    ]
    assert window.url_entry.text() == ""


@pytest.mark.unit
def test_apply_state_sets_widgets(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    state = {
        "urls": ["https://a.com", "https://b.com"],
        "output_dir": "data/output",  # project-relative path
        "use_proxy": True,
        "ignore_ssl": True,
        "download_images": False,
        "filter_site_chrome": False,
        "use_shared_browser": False,
    }
    window._apply_state(state)
    assert window.url_listbox.count() == 2
    assert window.output_entry.text().endswith(os.path.join("data", "output"))
    assert window.use_proxy_cb.isChecked() is True
    assert window.ignore_ssl_cb.isChecked() is True
    assert window.download_images_cb.isChecked() is False
    assert window.filter_site_chrome_cb.isChecked() is False
    assert window.use_shared_browser_cb.isChecked() is False


@pytest.mark.unit
def test_language_change_saves_settings_and_updates_status(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    # ensure combo has English and 中文; set to zh
    idx = window.lang_combo.findData("zh")
    assert idx != -1
    window._on_language_changed(idx)
    settings_file = Path(tmp_path) / "data" / "sessions" / "settings.json"
    assert settings_file.exists()
    # status should indicate restart required (in zh or en depending translation availability)
    assert window.status_label.text() != ""


@pytest.mark.unit
def test_convert_flow_calls_vm_start_and_updates_ui(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    window.url_listbox.addItem("https://example.com")
    with mock.patch.object(window.vm, "start") as start_mock:
        window._on_convert()
        # Button toggled to stop label
        assert window.is_running is True
        assert window.convert_btn.text() == window.translator.t("stop_button")
        # Progress prepared for one item
        assert window.progress.maximum() == 1
        start_mock.assert_called_once()


@pytest.mark.unit
def test_close_event_saves_last_state(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    window.url_listbox.addItem("https://a.com")
    window.use_proxy_cb.setChecked(True)
    window.ignore_ssl_cb.setChecked(True)
    window.download_images_cb.setChecked(False)
    window.filter_site_chrome_cb.setChecked(False)
    window.use_shared_browser_cb.setChecked(True)

    class _E:
        def accept(self):
            self.accepted = True

    e = _E()
    window.closeEvent(e)
    last = Path(tmp_path) / "data" / "sessions" / "last_state.json"
    assert last.exists()


@pytest.mark.unit
def test_restore_last_session_loads_and_applies(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    sessions = Path(tmp_path) / "data" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "last_state.json").write_text(
        '{"urls": ["https://a.com"], "output_dir":"data/output"}', encoding="utf-8"
    )
    window._restore_last_session()
    assert window.url_listbox.count() == 1


@pytest.mark.unit
def test_choose_output_dir_uses_dialog_return(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    with mock.patch(
        "markurldown.ui.pyside.gui.QFileDialog.getExistingDirectory",
        return_value=str(tmp_path),
    ):
        window._choose_output_dir()
        assert window.output_entry.text() == str(tmp_path)


@pytest.mark.unit
def test_stop_calls_vm_stop(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    with mock.patch.object(window.vm, "stop") as stop_mock:
        window._stop()
        stop_mock.assert_called_once()


@pytest.mark.unit
def test_on_event_thread_safe_delegates(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    with mock.patch.object(window, "_on_event") as on_event_mock:
        ev = ProgressEvent(kind="status", text="hi")
        window._on_event_thread_safe(ev)
        on_event_mock.assert_called_once()


@pytest.mark.unit
def test_on_event_branches_update_ui(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    t = window.translator.t

    window._on_event(
        ProgressEvent(kind="progress_init", total=3, key="convert_init", data={"total": 3})
    )
    assert window.progress.maximum() == 3

    window._on_event(ProgressEvent(kind="status", text="S"))
    assert window.status_label.text() == "S"

    window._on_event(ProgressEvent(kind="detail", text="D"))
    assert window.detail_label.text() == "D"

    window._on_event(ProgressEvent(kind="progress_step", data={"completed": 2}, text="step"))
    assert window.progress.value() == 2

    # fallback path without completed: increments by 1
    current = window.progress.value()
    window._on_event(ProgressEvent(kind="progress_step", text="step2"))
    assert window.progress.value() == current + 1

    window._on_event(ProgressEvent(kind="error", text="E"))
    assert window.is_running is False

    window._on_event(ProgressEvent(kind="stopped", text=t("status_stopped")))
    assert window.is_running is False

    window._on_event(ProgressEvent(kind="progress_done", text=t("status_done")))
    assert window.progress.value() == window.progress.maximum()


@pytest.mark.unit
def test_list_operations_move_delete_clear(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    window.url_listbox.addItem("a")
    window.url_listbox.addItem("b")
    window.url_listbox.addItem("c")
    window.url_listbox.setCurrentRow(1)  # b
    window._move_selected_up()
    assert [window.url_listbox.item(i).text() for i in range(window.url_listbox.count())] == [
        "b",
        "a",
        "c",
    ]
    window._move_selected_down()
    assert [window.url_listbox.item(i).text() for i in range(window.url_listbox.count())] == [
        "a",
        "b",
        "c",
    ]
    window._delete_selected()
    assert [window.url_listbox.item(i).text() for i in range(window.url_listbox.count())] == [
        "a",
        "c",
    ]
    window._clear_list()
    assert window.url_listbox.count() == 0


@pytest.mark.unit
def test_run_gui_entrypoint_is_callable(monkeypatch, tmp_path, qapp):
    # Patch heavy parts to avoid real GUI loop
    import markurldown.ui.pyside.gui as gui_mod

    fake_app = qapp
    splash_mock = mock.Mock()
    monkeypatch.setattr(gui_mod, "show_immediate_splash", lambda: (fake_app, splash_mock))
    monkeypatch.setattr(gui_mod, "load_json_from_root", lambda *args, **kwargs: {})
    created = {}

    class DummyWin:
        def __init__(self, *a, **kw):
            created["inst"] = self

        def show(self):
            created["shown"] = True

    monkeypatch.setattr(gui_mod, "PySideApp", DummyWin)
    # Prevent exec loop
    monkeypatch.setattr(fake_app, "exec", lambda: 0)

    gui_mod.run_gui()
    assert created.get("shown") is True
    splash_mock.finish.assert_called()


@pytest.mark.unit
def test_worker_emit_detail_variants(monkeypatch, tmp_path):
    # Exercise ConvertService._worker and its inner _emit_detail path
    from markurldown.services.convert_service import ConvertService

    svc = ConvertService()
    # Mock external dependencies
    monkeypatch.setattr(
        "markurldown.services.convert_service.build_requests_session", lambda **kw: object()
    )

    # Stub convert to call on_detail with dict and text, and return a minimal result-like object
    class _Result:
        def __init__(self):
            self.suggested_filename = "x.md"
            self.markdown = "# x"
            self.title = "t"

    def _stub_convert(payload, session, options):
        on_detail = payload.meta["on_detail"]
        on_detail({"key": "k", "data": {"a": 1}})
        on_detail("text line")
        return _Result()

    monkeypatch.setattr("markurldown.services.convert_service.registry_convert", _stub_convert)
    monkeypatch.setattr(
        "markurldown.services.convert_service.write_markdown",
        lambda out_dir, name, md: str(Path(tmp_path) / name),
    )

    events = []

    def _on_event(ev):
        events.append(ev)

    reqs = [SourceRequest(kind="url", value="https://e.com")]
    opts = ConversionOptions(
        use_proxy=False,
        ignore_ssl=True,
        download_images=False,
        filter_site_chrome=False,
        use_shared_browser=False,
    )

    svc._worker(reqs, str(tmp_path), opts, _on_event)
    # Ensure that detail events from both dict and text were emitted
    kinds = [e.kind for e in events]
    assert "detail" in kinds and "progress_done" in kinds


@pytest.mark.unit
def test_choose_and_import_export_are_mocked(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    sessions_dir = Path(tmp_path) / "data" / "sessions"
    export_target = sessions_dir / "session.json"
    window.url_listbox.addItem("https://x.com")
    # Mock save dialog
    with mock.patch(
        "markurldown.ui.pyside.gui.QFileDialog.getSaveFileName",
        return_value=(str(export_target), ""),
    ):
        window._export_session()
        assert export_target.exists()
    # Mock open dialog
    with mock.patch(
        "markurldown.ui.pyside.gui.QFileDialog.getOpenFileName",
        return_value=(str(export_target), ""),
    ):
        window._import_session()
        # After import, status/detail updated
        assert window.status_label.text() != ""
        assert window.detail_label.text() != ""


@pytest.mark.unit
def test_copy_selected_updates_clipboard_and_labels(tmp_path, qapp):
    window = _make_window(tmp_path, qapp)
    window.url_listbox.addItem("https://copy.me")
    window.url_listbox.setCurrentRow(0)
    window._copy_selected()
    clipboard = window.clipboard() if hasattr(window, "clipboard") else None
    # Fetch from QApplication clipboard directly
    from PySide6.QtWidgets import QApplication

    text = QApplication.clipboard().text()
    assert "copy.me" in text
    assert window.status_label.text() != ""
    assert window.detail_label.text() != ""
