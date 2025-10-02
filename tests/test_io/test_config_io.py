from __future__ import annotations

import json
import os

import pytest

from markdownall.io.config import load_config, load_json_from_root, save_config


@pytest.mark.unit
def test_save_and_load_config(tmp_path):
    p = tmp_path / "cfg.json"
    data = {"a": 1, "b": "x"}
    save_config(str(p), data)
    loaded = load_config(str(p))
    assert loaded == data


@pytest.mark.unit
def test_load_json_from_root_missing_and_invalid(tmp_path):
    # missing -> {}
    out = load_json_from_root(str(tmp_path), "settings.json")
    assert out == {}

    # invalid -> {}
    bad = tmp_path / "settings.json"
    bad.write_text("not json", encoding="utf-8")
    out = load_json_from_root(str(tmp_path), "settings.json")
    assert out == {}

    # valid json
    good = {"k": "v"}
    (tmp_path / "settings.json").write_text(json.dumps(good), encoding="utf-8")
    assert load_json_from_root(str(tmp_path), "settings.json") == good
