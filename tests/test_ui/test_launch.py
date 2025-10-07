import importlib
import sys
from types import ModuleType, SimpleNamespace


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
            AlignBottom=_Align.AlignBottom, AlignHCenter=_Align.AlignHCenter
        )

    class _QObject:
        def __init__(self, *args, **kwargs):
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
        def __init__(self, *_a, **_k):
            pass

    class _QColor:
        def __init__(self, *_a, **_k):
            pass

    class _QPixmap:
        def __init__(self, *args, **kwargs):
            self.size = args

        def fill(self, *_a, **_k):
            pass

    class _QApplication:
        _inst = None

        @classmethod
        def instance(cls):
            return cls._inst

        def __init__(self, *_a):
            type(self)._inst = self

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

    class _QMessageBox:
        @staticmethod
        def critical(*_a, **_k):
            pass

    class _QSplashScreen:
        def __init__(self, pixmap):
            self.pixmap = pixmap

        def show(self):
            self.shown = True

        def finish(self, _w):
            self.finished = True

    class _QStyleFactory:
        @staticmethod
        def keys():
            return ["Fusion"]

    # Minimal GUI classes for import-time subclassing and attribute access
    class _QMainWindow:
        def __init__(self, *a, **k):
            pass

        def setWindowIcon(self, *a, **k):
            pass

        def resize(self, *a, **k):
            pass

        def frameGeometry(self):
            class _G:
                def moveCenter(self, *a, **k):
                    pass

                def topLeft(self):
                    return (0, 0)

            return _G()

        def move(self, *a, **k):
            pass

        def setMinimumSize(self, *a, **k):
            pass

        def setCentralWidget(self, *a, **k):
            pass

        def update(self):
            pass

    class _QWidget: ...

    class _QLabel:
        def __init__(self, *a, **k):
            pass

        def setText(self, *a, **k):
            pass

        def setStyleSheet(self, *a, **k):
            pass

    class _QLineEdit:
        def __init__(self, *a, **k):
            pass

        def setStyleSheet(self, *a, **k):
            pass

        def sizeHint(self):
            return SimpleNamespace(height=lambda: 24)

        def setText(self, *a, **k):
            pass

        def text(self):
            return ""

        def setFocus(self):
            pass

        def returnPressed(self):
            return _Signal()

    class _QListWidget:
        def __init__(self, *a, **k):
            self._items = []

        def addItem(self, v):
            self._items.append(v)

        def count(self):
            return len(self._items)

        def item(self, i):
            return SimpleNamespace(text=lambda: self._items[i])

        def clear(self):
            self._items = []

        def currentRow(self):
            return 0

        def takeItem(self, idx):
            return None

        def insertItem(self, *a, **k):
            pass

        def setCurrentRow(self, *a, **k):
            pass

    class _QFrame: ...

    class _QPushButton:
        def __init__(self, *a, **k):
            self.clicked = _Signal()

        def setFixedHeight(self, *a, **k):
            pass

        def setFixedSize(self, *a, **k):
            pass

        def setFont(self, *a, **k):
            pass

        def setStyleSheet(self, *a, **k):
            pass

        def setText(self, *a, **k):
            pass

    class _QVBoxLayout:
        def __init__(self, *a, **k):
            pass

        def setSpacing(self, *a, **k):
            pass

        def setContentsMargins(self, *a, **k):
            pass

        def addWidget(self, *a, **k):
            pass

        def addLayout(self, *a, **k):
            pass

    class _QHBoxLayout(_QVBoxLayout):
        def setAlignment(self, *a, **k):
            pass

    class _QGridLayout(_QVBoxLayout):
        def addWidget(self, *a, **k):
            pass

        def setColumnStretch(self, *a, **k):
            pass

        def setRowStretch(self, *a, **k):
            pass

    class _QProgressBar:
        def __init__(self):
            self._value = 0
            self._max = 100

        def setVisible(self, *a, **k):
            pass

        def setRange(self, a, b):
            self._max = b

        def setValue(self, v):
            self._value = v

        def value(self):
            return self._value

        def maximum(self):
            return self._max

        def setStyleSheet(self, *a, **k):
            pass

    class _QComboBox:
        def __init__(self):
            self._items = []
            self.currentIndexChanged = _Signal()

        def addItem(self, *a, **k):
            self._items.append(a)

        def findData(self, *a, **k):
            return -1

        def setCurrentIndex(self, *a, **k):
            pass

    class _QFileDialog:
        @staticmethod
        def getExistingDirectory(*a, **k):
            return ""

        @staticmethod
        def getSaveFileName(*a, **k):
            return ("", None)

        @staticmethod
        def getOpenFileName(*a, **k):
            return ("", None)

    class _QCheckBox:
        def __init__(self, *a, **k):
            self._checked = False

        def setChecked(self, v):
            self._checked = bool(v)

        def isChecked(self):
            return self._checked

        def setText(self, *a, **k):
            pass

    class _QClipboard:
        def setText(self, *a, **k):
            pass

    class _QFont:
        Weight = SimpleNamespace(Bold=75)

        def __init__(self, *a, **k):
            pass

    class _QIcon:
        def __init__(self, *a, **k):
            pass

    qtcore.Qt = _Qt()
    qtcore.QObject = _QObject
    qtcore.QTimer = _QTimer
    qtcore.Signal = _Signal
    qtgui.QColor = _QColor
    qtgui.QPixmap = _QPixmap
    qtgui.QClipboard = _QClipboard
    qtgui.QFont = _QFont
    qtgui.QIcon = _QIcon
    qtwidgets.QApplication = _QApplication
    qtwidgets.QMessageBox = _QMessageBox
    qtwidgets.QSplashScreen = _QSplashScreen
    qtwidgets.QStyleFactory = _QStyleFactory
    qtwidgets.QMainWindow = _QMainWindow
    qtwidgets.QWidget = _QWidget
    qtwidgets.QLabel = _QLabel
    qtwidgets.QLineEdit = _QLineEdit
    qtwidgets.QListWidget = _QListWidget
    qtwidgets.QFrame = _QFrame
    qtwidgets.QPushButton = _QPushButton
    qtwidgets.QVBoxLayout = _QVBoxLayout
    qtwidgets.QHBoxLayout = _QHBoxLayout
    qtwidgets.QGridLayout = _QGridLayout
    qtwidgets.QProgressBar = _QProgressBar
    qtwidgets.QComboBox = _QComboBox
    qtwidgets.QFileDialog = _QFileDialog
    qtwidgets.QCheckBox = _QCheckBox

    fake_pkg.QtCore = qtcore
    fake_pkg.QtGui = qtgui
    fake_pkg.QtWidgets = qtwidgets

    monkeypatch.setitem(sys.modules, "PySide6", fake_pkg)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qtgui)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)


def test_launch_main_success(monkeypatch, tmp_path):
    # Change CWD to a temp project root
    monkeypatch.chdir(tmp_path)
    _install_fake_pyside(monkeypatch)

    # Prepare sessions dir and settings file scenario via stubbed loader
    captured_progress = []

    def fake_emit(app, splash, message: str):
        captured_progress.append(message)

    # Fake app/splash
    class FakeApp:
        def processEvents(self):
            pass

        def exec(self):
            pass

    class FakeSplash:
        def finish(self, _w):
            self.finished = True

    fake_app = FakeApp()
    fake_splash = FakeSplash()

    # Import module fresh to ensure clean state
    if "markdownall.launch" in sys.modules:
        del sys.modules["markdownall.launch"]
    launch = importlib.import_module("markdownall.launch")

    # Stubs for dependencies used in main
    monkeypatch.setattr(launch, "_emit_startup_progress", fake_emit)

    # Stub splash factory
    def fake_show_immediate_splash():
        return fake_app, fake_splash

    monkeypatch.setattr(launch, "show_immediate_splash", fake_show_immediate_splash)

    # Stub config loader to return Chinese language to exercise i18n branch
    def fake_load_json_from_root(_root, _name):
        return {"language": "zh"}

    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setattr(launch, "QMessageBox", SimpleNamespace(critical=lambda *a, **k: None))

    # Inject the loader symbol into the module namespace after it is imported inside main
    monkeypatch.setattr(
        importlib.import_module("markdownall.io.config"),
        "load_json_from_root",
        fake_load_json_from_root,
    )

    # Stub MainWindow class（入口统一为 MainWindow）
    created_args = {}

    class FakeWindow:
        def show(self):
            self.shown = True

    def fake_main_window(*, root_dir, settings):
        created_args["root_dir"] = root_dir
        created_args["settings"] = settings
        return FakeWindow()

    monkeypatch.setattr(
        importlib.import_module("markdownall.ui.pyside.main_window"),
        "MainWindow",
        staticmethod(lambda **kw: fake_main_window(**kw)),
    )

    # Run
    launch.main()

    # Assert messages sequence and content
    assert captured_progress[0] == "Loading settings…"
    # Chinese messages for zh
    assert "初始化" in captured_progress[1]
    assert "启动应用" in captured_progress[2]

    # Assert window was created with cwd and settings
    assert created_args["root_dir"] == str(tmp_path)
    assert created_args["settings"] == {"language": "zh"}


def test_launch_main_exception(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Import fresh
    # Ensure subsequent attribute patches apply to the same module object
    _install_fake_pyside(monkeypatch)
    if "markdownall.launch" in sys.modules:
        del sys.modules["markdownall.launch"]
    launch = importlib.import_module("markdownall.launch")

    # Minimal app/QMessageBox stubs
    class FakeApp:
        @staticmethod
        def instance():
            return None

        def __init__(self, *_a):
            pass

        def exec(self):
            pass

    critical_calls = {}

    def fake_critical(parent, title, text):
        critical_calls["title"] = title
        critical_calls["text"] = text

    # Stub splash creation
    class FakeSplash:
        def finish(self, _w):
            pass

    def fake_show_immediate_splash():
        return FakeApp(), FakeSplash()

    monkeypatch.setattr(launch, "show_immediate_splash", fake_show_immediate_splash)

    # Ensure progress emitter doesn't touch Qt specifics
    monkeypatch.setattr(launch, "_emit_startup_progress", lambda *a, **k: None)

    # Make MainWindow raise
    def raising_main_window(**_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        importlib.import_module("markdownall.ui.pyside.main_window"),
        "MainWindow",
        staticmethod(lambda **kw: raising_main_window(**kw)),
    )

    # Stub config loader to return empty
    monkeypatch.setattr(
        importlib.import_module("markdownall.io.config"), "load_json_from_root", lambda *a, **k: {}
    )

    # Stub QMessageBox and QApplication in module namespace
    monkeypatch.setattr(launch, "QApplication", FakeApp)
    monkeypatch.setattr(launch, "QMessageBox", SimpleNamespace(critical=fake_critical))

    try:
        launch.main()
        raised = False
    except Exception as e:
        raised = True
        assert str(e) == "boom"

    assert raised is True
    assert critical_calls.get("title") == "MarkdownAll"
    assert "Failed to start" in critical_calls.get("text", "")


def test_emit_startup_progress_invokes_qt_and_process_events(monkeypatch):
    # Arrange fake PySide and import launch module
    _install_fake_pyside(monkeypatch)
    import importlib

    if "markdownall.launch" in sys.modules:
        del sys.modules["markdownall.launch"]
    launch = importlib.import_module("markdownall.launch")

    # Capture showMessage arguments
    captured = {}

    class FakeSplash:
        def showMessage(self, message, alignment, color):
            captured["message"] = message
            captured["alignment"] = alignment
            captured["color_class"] = type(color).__name__

    class FakeApp:
        def __init__(self):
            self.processed = False

        def processEvents(self):
            self.processed = True

    app = FakeApp()
    splash = FakeSplash()

    # Act
    launch._emit_startup_progress(app, splash, "Hello")

    # Assert
    assert captured["message"] == "Hello"
    # Alignment should OR bottom and hcenter (1 | 2 == 3)
    assert captured["alignment"] == 3
    # Color class comes from fake PySide _QColor
    assert captured["color_class"].lower().endswith("qcolor")
    assert app.processed is True
