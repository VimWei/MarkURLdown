from __future__ import annotations

# Force headless platform early for collection phase
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Preemptively patch QSplashScreen at module import time to avoid platform crashes
try:
    # Patch at PySide6 layer
    from PySide6 import QtWidgets as _QtW

    class _FakeQSplash:
        def __init__(self, *_a, **_k):
            self._visible = False

        def show(self):
            self._visible = True

        def isVisible(self):
            return self._visible

        def finish(self, _w):
            self._visible = False

        def close(self):
            self._visible = False

        def showMessage(self, *_a, **_k):
            pass

    setattr(_QtW, "QSplashScreen", _FakeQSplash)

    # If splash module is already imported during collection, patch its bound symbol too
    try:
        import markdownall.ui.pyside.splash as _splash_mod

        setattr(_splash_mod, "QSplashScreen", _FakeQSplash)
    except Exception:
        pass
except Exception:
    pass

import sys

import pytest

# Ensure Qt runs in offscreen mode for headless testing environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    # Do not quit explicitly; PySide can manage cleanup on interpreter exit


"""pytest 配置文件"""

from unittest.mock import Mock

import pytest

from markdownall.app_types import ConversionOptions


@pytest.fixture
def mock_session():
    """提供模拟的请求会话"""
    session = Mock()
    session.headers = {}
    session.cookies = {}
    return session


@pytest.fixture
def default_options():
    """提供默认的转换选项"""
    return ConversionOptions(
        ignore_ssl=False,
        use_proxy=False,
        download_images=True,
        filter_site_chrome=True,
        use_shared_browser=True,
    )


@pytest.fixture
def mock_weixin_url():
    """提供模拟的微信文章URL"""
    return "https://mp.weixin.qq.com/s/test_article_id"


@pytest.fixture
def mock_zhihu_url():
    """提供模拟的知乎文章URL"""
    return "https://zhuanlan.zhihu.com/p/test_article_id"


@pytest.fixture
def mock_generic_url():
    """提供模拟的通用网站URL"""
    return "https://example.com/article"


@pytest.fixture
def sample_html():
    """提供示例HTML内容"""
    return """
    <html>
        <head>
            <title>测试文章标题</title>
        </head>
        <body>
            <article>
                <h1>测试文章标题</h1>
                <p>这是测试文章的内容。</p>
                <img src="https://example.com/image.jpg" alt="测试图片">
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_markdown():
    """提供示例Markdown内容"""
    return """# 测试文章标题

这是测试文章的内容。

![测试图片](https://example.com/image.jpg)
"""


@pytest.fixture(autouse=True)
def setup_test_environment():
    """自动设置测试环境"""
    # 这里可以设置测试环境变量、清理临时文件等
    pass


@pytest.fixture(autouse=True)
def prevent_blocking_qt_dialogs(monkeypatch):
    """Prevent modal Qt dialogs from blocking in headless/test runs.

    Individual tests can override with mock.patch/monkeypatch as needed.
    """
    # Patch at the module-under-test level to ensure dialogs never block
    # 过去会对 gui 模块做桩替换；现在直接针对 PySide6 做桩即可

    # Also patch at the PySide6 layer
    try:
        from PySide6 import QtWidgets as QtW

        # Safe defaults; tests can override
        if hasattr(QtW, "QFileDialog"):
            if not hasattr(QtW.QFileDialog, "getExistingDirectory"):
                setattr(QtW.QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
            else:
                monkeypatch.setattr(
                    QtW.QFileDialog, "getExistingDirectory", lambda *a, **k: "", raising=False
                )
            if not hasattr(QtW.QFileDialog, "getOpenFileName"):
                setattr(QtW.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
            else:
                monkeypatch.setattr(
                    QtW.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""), raising=False
                )
            if not hasattr(QtW.QFileDialog, "getSaveFileName"):
                setattr(QtW.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
            else:
                monkeypatch.setattr(
                    QtW.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""), raising=False
                )

        # Ensure QMessageBox APIs are non-blocking in tests
        monkeypatch.setattr(QtW.QMessageBox, "critical", lambda *a, **k: None, raising=False)
        monkeypatch.setattr(QtW.QMessageBox, "exec", lambda *a, **k: 0, raising=False)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def silence_external_openers(monkeypatch):
    """Silence OS openers like explorer/open/xdg-open during tests.

    Prevents tests from actually opening system file browsers when code calls
    subprocess.run(["explorer"|"open"|"xdg-open", path]). Other subprocess.run
    calls are forwarded to the real implementation.
    """
    import subprocess as _sp

    real_run = _sp.run

    def _quiet_run(args, *pargs, **kwargs):
        try:
            cmd = args[0] if isinstance(args, (list, tuple)) and args else args
            if isinstance(cmd, str):
                opener = cmd
            else:
                opener = cmd
            if opener in ("explorer", "open", "xdg-open"):
                return None
        except Exception:
            pass
        return real_run(args, *pargs, **kwargs)

    monkeypatch.setattr("subprocess.run", _quiet_run, raising=False)


def pytest_configure(config):
    """pytest 配置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "slow: 标记为慢速测试")
    config.addinivalue_line("markers", "integration: 标记为集成测试")
    config.addinivalue_line("markers", "unit: 标记为单元测试")
