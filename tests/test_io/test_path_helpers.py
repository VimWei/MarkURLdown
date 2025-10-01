from __future__ import annotations

import os
from pathlib import Path

import pytest

from markurldown.io.config import resolve_project_path, to_project_relative_path


@pytest.mark.unit
def test_to_project_relative_path_inside_root(tmp_path):
    project_root = tmp_path
    inside = tmp_path / "data" / "output" / "sspai"
    inside.mkdir(parents=True, exist_ok=True)

    stored = to_project_relative_path(str(inside), str(project_root))
    # Should be leading slash and POSIX separators
    assert stored.startswith("/")
    assert stored.replace("\\", "/").startswith("/data/output/sspai")


@pytest.mark.unit
def test_to_project_relative_path_outside_root(tmp_path):
    project_root = tmp_path
    outside = tmp_path.parent / (tmp_path.name + "_outside") / "any"
    outside.mkdir(parents=True, exist_ok=True)

    stored = to_project_relative_path(str(outside), str(project_root))
    # Outside root: keep absolute path
    assert os.path.isabs(stored)
    assert stored == os.path.abspath(str(outside))


@pytest.mark.unit
def test_to_project_relative_path_relpath_value_error(monkeypatch, tmp_path):
    project_root = tmp_path
    target = tmp_path / "data"
    target.mkdir(exist_ok=True)

    def raise_value_error(*args, **kwargs):  # type: ignore[no-redef]
        raise ValueError("relpath error")

    monkeypatch.setattr(os.path, "relpath", raise_value_error)
    stored = to_project_relative_path(str(target), str(project_root))
    # On relpath error: keep original
    assert stored == str(target)


@pytest.mark.unit
def test_resolve_project_path_from_slash_relative(tmp_path):
    project_root = tmp_path
    stored = "/data/output/site"
    resolved = resolve_project_path(stored, str(project_root))
    assert resolved == os.path.abspath(os.path.join(str(project_root), "data", "output", "site"))


@pytest.mark.unit
def test_resolve_project_path_from_plain_relative(tmp_path):
    project_root = tmp_path
    stored = "data/output/site"
    resolved = resolve_project_path(stored, str(project_root))
    assert resolved == os.path.abspath(os.path.join(str(project_root), stored))


@pytest.mark.unit
def test_resolve_project_path_from_absolute(tmp_path):
    project_root = tmp_path
    absolute = tmp_path / "abs" / "path"
    absolute.mkdir(parents=True, exist_ok=True)
    resolved = resolve_project_path(str(absolute), str(project_root))
    assert resolved == str(absolute)
