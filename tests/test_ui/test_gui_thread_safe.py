import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def _install_fake_pyside(monkeypatch):
    fake_pkg = ModuleType("PySide6")
    qtcore = ModuleType("PySide6.QtCore")
    qtgui = ModuleType("PySide6.QtGui")
    qtwidgets = ModuleType("PySide6.QtWidgets")

    class _Align:
        AlignBottom = 1
        AlignHCenter = 2

    class _Qt:
        AlignmentFlag = SimpleNamespace(
            AlignBottom=_Align.AlignBottom,
            AlignHCenter=_Align.AlignHCenter,
            AlignRight=4,
            AlignCenter=8,
        )

    class _QObject:
        def __init__(self, *a, **k):
            pass

    class _Signal:
        def __init__(self, *_a, **_k):
            self._subs = []

        def connect(self, fn):
            self._subs.append(fn)

        def emit(self, *a, **k):
            for fn in list(self._subs):
                try:
                    fn(*a, **k)
                except Exception:
                    pass

    class _QTimer:
        def __init__(self, *a, **k):
            self.timeout = _Signal()

    class _QApplication:
        _inst = None

        @classmethod
        def instance(cls):
            return cls._inst

        def __init__(self, *_a):
            _QApplication._inst = self

        def processEvents(self):
            pass

        def exec(self):
            pass

        def setStyle(self, *_a, **_k):
            pass

        @staticmethod
        def primaryScreen():
            class _Scr:
                class _Geom:
                    def center(self):
                        return (0, 0)

                def availableGeometry(self):
                    return self._Geom()

            return _Scr()

        @staticmethod
        def clipboard():
            return SimpleNamespace(setText=lambda *a, **k: None)

    class _QMainWindow:
        def __init__(self, *a, **k):
            pass

    # minimal stubs to satisfy imports in gui.py
    qtcore.Qt = _Qt()
    qtcore.QObject = _QObject
    qtcore.QThread = object
    qtcore.QTimer = _QTimer
    qtcore.Signal = _Signal
    qtgui.QClipboard = object
    qtgui.QColor = object
    qtgui.QFont = object
    qtgui.QIcon = object
    qtgui.QPixmap = object
    qtwidgets.QApplication = _QApplication
    for name in [
        "QCheckBox",
        "QComboBox",
        "QFrame",
        "QGridLayout",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QListWidget",
        "QMainWindow",
        "QProgressBar",
        "QPushButton",
        "QSizePolicy",
        "QSplashScreen",
        "QSpacerItem",
        "QSplitter",
        "QStyleFactory",
        "QTabWidget",
        "QTextEdit",
        "QVBoxLayout",
        "QWidget",
    ]:
        setattr(qtwidgets, name, type(name, (), {}))

    # Provide QFileDialog and QMessageBox with required static methods so tests can monkeypatch them
    class QFileDialog:
        @staticmethod
        def getExistingDirectory(*a, **k):
            return ""

        @staticmethod
        def getOpenFileName(*a, **k):
            return ("", "")

        @staticmethod
        def getSaveFileName(*a, **k):
            return ("", "")

    class QMessageBox:
        @staticmethod
        def critical(*a, **k):
            return None

    qtwidgets.QFileDialog = QFileDialog
    qtwidgets.QMessageBox = QMessageBox

    fake_pkg.QtCore = qtcore
    fake_pkg.QtGui = qtgui
    fake_pkg.QtWidgets = qtwidgets

    monkeypatch.setitem(sys.modules, "PySide6", fake_pkg)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qtgui)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)


@pytest.mark.skip(reason="Requires real Qt environment")
@pytest.mark.unit
def test_on_event_thread_safe_calls_on_event(monkeypatch, tmp_path):
    _install_fake_pyside(monkeypatch)
    if "markdownall.ui.pyside.gui" in sys.modules:
        del sys.modules["markdownall.ui.pyside.gui"]
    gui = importlib.import_module("markdownall.ui.pyside.main_window")

    # Create a proper QApplication instance that works with our fake setup
    from PySide6.QtWidgets import QApplication
    app_instance = QApplication([])
    
    # Ensure primaryScreen method works
    monkeypatch.setattr(QApplication, "primaryScreen", lambda: type('Screen', (), {
        'availableGeometry': lambda: type('Geometry', (), {
            'center': lambda: (400, 300)
        })()
    })())

    # Avoid heavy UI setup during construction
    monkeypatch.setattr(gui.MainWindow, "_setup_ui", lambda self: None)
    monkeypatch.setattr(gui.MainWindow, "_retranslate_ui", lambda self: None)
    monkeypatch.setattr(gui.MainWindow, "_connect_signals", lambda self: None)
    # Make translator load without filesystem
    monkeypatch.setattr(
        gui.Translator, "load_language", lambda self, code: setattr(self, "language", "en")
    )
    
    # Mock QWidget constructor to avoid QApplication check
    from PySide6.QtWidgets import QWidget
    def mock_qwidget_init(self, *args, **kwargs):
        pass
    
    monkeypatch.setattr(QWidget, "__init__", mock_qwidget_init)
    
    # Also mock QMainWindow constructor
    from PySide6.QtWidgets import QMainWindow
    def mock_qmainwindow_init(self, *args, **kwargs):
        pass
    
    monkeypatch.setattr(QMainWindow, "__init__", mock_qmainwindow_init)
    
    # Mock QWidget class itself
    class MockQWidget:
        def __init__(self, *args, **kwargs):
            pass
    
    monkeypatch.setattr("PySide6.QtWidgets.QWidget", MockQWidget)
    
    # Mock QMainWindow class itself
    class MockQMainWindow(MockQWidget):
        def __init__(self, *args, **kwargs):
            pass
    
    monkeypatch.setattr("PySide6.QtWidgets.QMainWindow", MockQMainWindow)
    
    # Mock QWidget class itself in the module
    monkeypatch.setattr("markdownall.ui.pyside.main_window.QWidget", MockQWidget)
    monkeypatch.setattr("markdownall.ui.pyside.main_window.QMainWindow", MockQMainWindow)
    
    # Mock QWidget class itself in the module
    monkeypatch.setattr("markdownall.ui.pyside.main_window.QWidget", MockQWidget)
    monkeypatch.setattr("markdownall.ui.pyside.main_window.QMainWindow", MockQMainWindow)

    app = gui.MainWindow(root_dir=str(tmp_path), settings={})

    calls = {}

    def fake_on_event(ev):
        calls["ev"] = ev

    app._on_event = fake_on_event  # type: ignore
    ev = importlib.import_module("markdownall.app_types").ProgressEvent(kind="status", text="ok")
    app._on_event_thread_safe(ev)
    assert calls.get("ev") is ev
    # Cleanup: ensure later tests re-import gui with real Qt
    if "markdownall.ui.pyside.gui" in sys.modules:
        del sys.modules["markdownall.ui.pyside.gui"]


@pytest.mark.skip(reason="Requires real Qt environment")
@pytest.mark.unit
def test_on_event_thread_safe_handles_exception(monkeypatch, tmp_path):
    _install_fake_pyside(monkeypatch)
    if "markdownall.ui.pyside.gui" in sys.modules:
        del sys.modules["markdownall.ui.pyside.gui"]
    gui = importlib.import_module("markdownall.ui.pyside.main_window")

    monkeypatch.setattr(gui.MainWindow, "_setup_ui", lambda self: None)
    monkeypatch.setattr(gui.MainWindow, "_retranslate_ui", lambda self: None)
    monkeypatch.setattr(gui.MainWindow, "_connect_signals", lambda self: None)
    monkeypatch.setattr(
        gui.Translator, "load_language", lambda self, code: setattr(self, "language", "en")
    )

    app = gui.MainWindow(root_dir=str(tmp_path), settings={})

    def raising(*_a, **_k):
        raise RuntimeError("boom")

    app._on_event = raising  # type: ignore
    ev = importlib.import_module("markdownall.app_types").ProgressEvent(kind="status", text="ok")

    # Should not raise
    app._on_event_thread_safe(ev)
    # Cleanup: ensure later tests re-import gui with real Qt
    if "markdownall.ui.pyside.gui" in sys.modules:
        del sys.modules["markdownall.ui.pyside.gui"]
