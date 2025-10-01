from __future__ import annotations

import builtins
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from unittest import mock

import pytest


def import_version_with_uv(stdout: str = "0.7.2\n"):
    completed = types.SimpleNamespace(stdout=stdout)
    with mock.patch("subprocess.run", return_value=completed):
        # Load module from file path to ensure patches apply during execution
        path = Path(__file__).parent.parent.parent / "src" / "markurldown" / "version.py"
        spec = importlib.util.spec_from_file_location("markurldown.version_tested", str(path))
        mod = importlib.util.module_from_spec(spec)
        loader = spec.loader
        assert loader is not None
        loader.exec_module(mod)
        return mod


def import_version_with_pyproject(ver: str = "1.2.3"):
    # Force uv missing and provide pyproject contents
    fake_pyproject = f"""
[project]
name = "x"
version = "{ver}"
"""
    m = mock.mock_open(read_data=fake_pyproject)
    with (
        mock.patch("subprocess.run", side_effect=FileNotFoundError()),
        mock.patch.object(builtins, "open", m),
    ):
        path = Path(__file__).parent.parent.parent / "src" / "markurldown" / "version.py"
        spec = importlib.util.spec_from_file_location("markurldown.version_tested", str(path))
        mod = importlib.util.module_from_spec(spec)
        loader = spec.loader
        assert loader is not None
        loader.exec_module(mod)
        return mod


@pytest.mark.unit
def test_get_version_uses_uv_success():
    version = import_version_with_uv()
    # Module-level computed during import
    assert version.__version__ == "0.7.2"


@pytest.mark.unit
def test_get_version_fallback_to_pyproject(monkeypatch):
    version = import_version_with_pyproject("1.2.3")
    assert version.__version__ == "1.2.3"


@pytest.mark.unit
def test_get_version_info_parsing(monkeypatch):
    version = import_version_with_pyproject("1.2.3")
    monkeypatch.setattr(version, "get_version", lambda: "1.2.3")
    assert version.get_version_info() == (1, 2, 3)


@pytest.mark.unit
def test_is_prerelease(monkeypatch):
    version = import_version_with_pyproject("1.2.3a1")
    monkeypatch.setattr(version, "get_version", lambda: "1.2.3a1")
    assert version.is_prerelease() is True
    monkeypatch.setattr(version, "get_version", lambda: "1.2.3")
    assert version.is_prerelease() is False


@pytest.mark.unit
def test_compare_version(monkeypatch):
    version = import_version_with_pyproject("1.2.3")
    monkeypatch.setattr(version, "get_version_info", lambda: (1, 2, 3))
    assert version.compare_version("1.2.4") == -1
    assert version.compare_version("1.2.3") == 0
    assert version.compare_version("1.2.2") == 1


@pytest.mark.unit
def test_get_version_display(monkeypatch):
    version = import_version_with_pyproject("1.0.0")
    monkeypatch.setattr(version, "get_version", lambda: "1.0.0")
    assert version.get_version_display() == "v1.0.0"


@pytest.mark.unit
def test_module_level_version_reload(monkeypatch):
    # Reload using patches so module-level __version__ is set
    path = Path(__file__).parent.parent.parent / "src" / "markurldown" / "version.py"
    fake_pyproject = """
[project]
name = "x"
version = "9.9.9"
"""
    m = mock.mock_open(read_data=fake_pyproject)
    with (
        mock.patch("subprocess.run", side_effect=FileNotFoundError()),
        mock.patch.object(builtins, "open", m),
    ):
        spec = importlib.util.spec_from_file_location(
            "markurldown.version_tested_reload", str(path)
        )
        reloaded = importlib.util.module_from_spec(spec)
        loader = spec.loader
        assert loader is not None
        loader.exec_module(reloaded)
    assert reloaded.__version__ == "9.9.9"
    assert reloaded.__version_info__ == (9, 9, 9)


@pytest.mark.unit
def test_get_about_text(monkeypatch):
    version = import_version_with_pyproject("2.0.0")
    fake_info = {
        "version": "2.0.0",
        "version_info": (2, 0, 0),
        "display": "v2.0.0",
        "is_prerelease": False,
        "major": 2,
        "minor": 0,
        "patch": 0,
    }
    monkeypatch.setattr(version, "get_full_version_info", lambda: fake_info)
    txt = version.get_about_text()
    assert "MarkURLdown v2.0.0" in txt
    assert "Version: 2.0.0" in txt
