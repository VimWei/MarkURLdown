from __future__ import annotations

from unittest import mock

import pytest

from markurldown.services import playwright_driver as drv


class DummyPage:
    def __init__(self):
        self.scripts = []
        self.timeout = None
        self.closed = False
        self._visible = True
        self._content = "<html></html>"
        self._title = "T"
        self.keyboard = mock.Mock()

    def add_init_script(self, js: str):
        self.scripts.append(js)

    def set_default_timeout(self, ms: int):
        self.timeout = ms

    def query_selector(self, selector: str):
        # return a mock element that is visible and clickable
        btn = mock.Mock()
        btn.is_visible.return_value = self._visible
        return btn

    def evaluate(self, script: str, arg):
        return None

    def wait_for_timeout(self, ms: int):
        return None

    def content(self):
        return self._content

    def title(self):
        return self._title

    def close(self):
        self.closed = True


class DummyContext:
    def __init__(self):
        self.closed = False
        self.page = DummyPage()

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class DummyBrowser:
    def __init__(self):
        self.created = []

    def new_context(self, **options):
        self.created.append(options)
        return DummyContext()


@pytest.mark.unit
def test_new_context_and_page_apply_stealth_by_default():
    br = DummyBrowser()
    ctx, page = drv.new_context_and_page(br)
    # page created and stealth applied (scripts injected and timeout set)
    assert isinstance(page, DummyPage)
    assert page.scripts and page.timeout == 30000


@pytest.mark.unit
def test_new_context_and_page_no_stealth_sets_timeout_only():
    br = DummyBrowser()
    ctx, page = drv.new_context_and_page(br, apply_stealth=False)
    assert isinstance(page, DummyPage)
    assert page.timeout == 30000
    # No stealth scripts when disabled
    assert page.scripts == []


@pytest.mark.unit
def test_new_context_and_page_context_options_merge():
    br = DummyBrowser()
    overrides = {"viewport": {"width": 1366, "height": 768}, "extra_http_headers": {"X-Test": "1"}}
    ctx, page = drv.new_context_and_page(br, context_options=overrides)
    assert br.created, "new_context not called"
    opts = br.created[-1]
    assert opts["viewport"]["width"] == 1366
    assert opts["extra_http_headers"].get("X-Test") == "1"


@pytest.mark.unit
def test_teardown_ignores_errors():
    ctx = DummyContext()
    page = ctx.page
    # Force close to raise on first call
    page.close = mock.Mock(side_effect=Exception("boom"))
    ctx.close = mock.Mock(side_effect=Exception("boom"))
    # Should not raise
    drv.teardown_context_page(ctx, page)


@pytest.mark.unit
def test_apply_stealth_and_defaults_safe():
    p = DummyPage()
    drv.apply_stealth_and_defaults(p, default_timeout_ms=12345)
    assert p.timeout == 12345
    assert p.scripts


@pytest.mark.unit
def test_try_close_modal_with_selectors_success_path():
    p = DummyPage()
    ok = drv.try_close_modal_with_selectors(
        p, selectors=[".close", "#x"], modal_detection_selectors=[".modal"]
    )
    assert ok is True


@pytest.mark.unit
def test_try_close_modal_with_selectors_escape_fallback():
    p = DummyPage()
    # Make clicks fail to trigger Escape fallback
    elem = mock.Mock()
    elem.is_visible.return_value = True
    elem.click.side_effect = Exception("fail")
    p.query_selector = mock.Mock(return_value=elem)
    # Also make evaluate fail so selectors path cannot close
    p.evaluate = mock.Mock(side_effect=Exception("nope"))
    ok = drv.try_close_modal_with_selectors(
        p, selectors=[".close"], modal_detection_selectors=[".modal"], use_escape_fallback=True
    )
    assert ok is True
    p.keyboard.press.assert_called_with("Escape")


@pytest.mark.unit
def test_try_close_modal_with_selectors_detection_absent_returns_true():
    p = DummyPage()

    # modal_detection_selectors provided but none present
    def qsel(selector):
        if selector == ".modal":
            return None
        return None

    p.query_selector = mock.Mock(side_effect=qsel)
    ok = drv.try_close_modal_with_selectors(
        p, selectors=[".close"], modal_detection_selectors=[".modal"], use_escape_fallback=True
    )
    assert ok is True
    p.keyboard.press.assert_not_called()


@pytest.mark.unit
def test_wait_for_selector_stable_with_mapping_and_timeout():
    p = DummyPage()
    p.wait_for_selector = mock.Mock(side_effect=Exception("timeout"))
    drv.wait_for_selector_stable(p, {"unknown": ".main"}, page_type_key="post", timeout_ms=10)
    p.wait_for_selector.assert_called()


@pytest.mark.unit
def test_read_page_content_and_title_emits_and_reads():
    p = DummyPage()
    messages = []
    html, title = drv.read_page_content_and_title(p, on_detail=messages.append)
    assert html.startswith("<html") and title == "T"
    assert any("获取页面内容" in str(m) for m in messages)
