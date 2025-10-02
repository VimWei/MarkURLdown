from __future__ import annotations

import os
from unittest import mock

import pytest

from markdownall.ui.pyside.gui import Translator
from markdownall.ui.pyside.splash import _pick_splash_image, show_immediate_splash


@pytest.mark.unit
def test_translator_load_language_auto_and_fallback(tmp_path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    # only provide en.json to force fallback behavior
    (locales_dir / "en.json").write_text('{"greeting": "Hello {name}"}', encoding="utf-8")

    tr = Translator(str(locales_dir))
    with mock.patch("locale.getdefaultlocale", return_value=("zz_ZZ", "UTF-8")):
        tr.load_language("auto")

    assert tr.language == "en"
    assert tr.t("greeting", name="World") == "Hello World"
    # unknown key should return key itself
    assert tr.t("unknown_key") == "unknown_key"


@pytest.mark.unit
def test_pick_splash_image_returns_pixmap(qapp):
    pix = _pick_splash_image()
    # Should always return a QPixmap, even when assets are missing
    from PySide6.QtGui import QPixmap

    assert isinstance(pix, QPixmap)


@pytest.mark.unit
def test_show_immediate_splash_shows_and_returns(qapp):
    app, splash = show_immediate_splash()
    # The returned app must be the same QApplication instance
    from PySide6.QtWidgets import QApplication

    assert app is QApplication.instance()
    assert splash.isVisible()
    # Close splash promptly to avoid affecting other tests
    splash.close()
