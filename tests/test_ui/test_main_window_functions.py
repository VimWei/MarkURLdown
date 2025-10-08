from __future__ import annotations

from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QShowEvent

from markdownall.ui.pyside.main_window import MainWindow


def _make_window(tmp_path):
    app = QApplication.instance() or QApplication([])
    return MainWindow(str(tmp_path))


def test_on_show_event_calls_timer(tmp_path):
    mw = _make_window(tmp_path)
    ev = QShowEvent()
    with patch('PySide6.QtCore.QTimer.singleShot') as mock_timer:
        # Call method body to ensure lines are executed
        mw._on_show_event(ev)
        assert mock_timer.called


def test_force_splitter_config_executes(tmp_path):
    mw = _make_window(tmp_path)
    mw.splitter = Mock()
    mw.splitter.sizes.return_value = [300, 120, 200]
    with patch.object(mw, 'height', return_value=700):
        with patch('PySide6.QtCore.QTimer.singleShot'):
            mw._force_splitter_config()
    # verify invoked
    assert mw.splitter.setSizes.called


def test_reinforce_splitter_memory_executes(tmp_path):
    mw = _make_window(tmp_path)
    mw.splitter = Mock()
    mw.splitter.sizes.return_value = [250, 120, 200]
    with patch.object(mw, 'height', return_value=700):
        mw.remembered_tab_height = 300
        mw._reinforce_splitter_memory()
    assert mw.splitter.setSizes.called


def test_sync_ui_from_config_executes(tmp_path):
    mw = _make_window(tmp_path)
    # Stub pages/components with required methods
    mw.basic_page = Mock(); mw.webpage_page = Mock(); mw.advanced_page = Mock(); mw.command_panel = Mock(); mw.log_panel = Mock()
    cfg = {
        'basic': {},
        'webpage': {},
        'advanced': {},
    }
    mw._sync_ui_from_config()
    # At least called set_config on pages/components when available
    assert mw.basic_page.set_config.called or mw.webpage_page.set_config.called or mw.advanced_page.set_config.called


def test_on_performance_warning_executes(tmp_path):
    mw = _make_window(tmp_path)
    mw.log_panel = Mock()
    mw._on_performance_warning("warn")
    assert mw.log_panel.appendLog.called
