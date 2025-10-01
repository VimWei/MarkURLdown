from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from unittest import mock

import pytest


def import_version_with(ver: str):
    path = Path(__file__).parent.parent.parent / "markurldown" / "version.py"
    spec = importlib.util.spec_from_file_location("markurldown.version_tested_extra", str(path))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    # Override getter directly on loaded module to control behavior
    mod.get_version = lambda: ver  # type: ignore[attr-defined]
    return mod


@pytest.mark.unit
def test_get_full_version_info_and_app_title():
    v = import_version_with("1.2.3")
    info = v.get_full_version_info()
    assert info["version"] == "1.2.3" and info["version_info"] == (1, 2, 3)
    assert v.get_app_title().startswith("MarkURLdown v")
