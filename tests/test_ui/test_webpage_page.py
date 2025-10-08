"""Test WebpagePage functionality."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.pages.webpage_page import WebpagePage


class TestWebpagePage:
    """Test WebpagePage class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.mock_translator = Mock()
        self.mock_translator.t = Mock(side_effect=lambda key, **kwargs: f"translated_{key}")

        self.webpage_page = WebpagePage(translator=self.mock_translator)

    def test_emit_options_changed(self):
        """Test _emit_options_changed method."""
        with patch.object(
            self.webpage_page, "get_options", return_value={"use_proxy": True}
        ) as mock_get_options:
            with patch.object(self.webpage_page, "optionsChanged") as mock_signal:
                self.webpage_page._emit_options_changed()

                mock_get_options.assert_called_once()
                mock_signal.emit.assert_called_once_with({"use_proxy": True})

    def test_initialization(self):
        """Test WebpagePage initialization."""
        assert self.webpage_page.translator == self.mock_translator
        assert self.webpage_page.use_proxy_var is False
        assert self.webpage_page.ignore_ssl_var is False
        assert self.webpage_page.download_images_var is True
        assert self.webpage_page.filter_site_chrome_var is True
        assert self.webpage_page.use_shared_browser_var is True
        assert hasattr(self.webpage_page, "optionsChanged")
        assert isinstance(self.webpage_page._options_changed_timer, QTimer)

    def test_initialization_without_translator(self):
        """Test WebpagePage initialization without translator."""
        page = WebpagePage(translator=None)
        assert page.translator is None
        assert page.use_proxy_var is False
        assert page.ignore_ssl_var is False
        assert page.download_images_var is True
        assert page.filter_site_chrome_var is True
        assert page.use_shared_browser_var is True

    def test_timer_configuration(self):
        """Test that the debounce timer is properly configured."""
        timer = self.webpage_page._options_changed_timer
        assert timer.isSingleShot() is True
        assert timer.interval() == 50

    def test_signal_connections(self):
        """Test that checkbox signals are properly connected."""
        # Test that all checkboxes are connected to _on_option_changed
        with patch.object(self.webpage_page, "_on_option_changed") as mock_handler:
            # Simulate checkbox state changes
            self.webpage_page.use_proxy_cb.stateChanged.emit(1)
            self.webpage_page.ignore_ssl_cb.stateChanged.emit(1)
            self.webpage_page.download_images_cb.stateChanged.emit(1)
            self.webpage_page.filter_site_chrome_cb.stateChanged.emit(1)
            self.webpage_page.use_shared_browser_cb.stateChanged.emit(1)

            # Should be called 5 times (once for each checkbox)
            assert mock_handler.call_count == 5

    def test_on_option_changed_timer_restart(self):
        """Test _on_option_changed method restarts timer."""
        with patch.object(self.webpage_page._options_changed_timer, "isActive", return_value=True):
            with patch.object(self.webpage_page._options_changed_timer, "stop") as mock_stop:
                with patch.object(self.webpage_page._options_changed_timer, "start") as mock_start:
                    self.webpage_page._on_option_changed()

                    mock_stop.assert_called_once()
                    mock_start.assert_called_once()

    def test_on_option_changed_timer_start(self):
        """Test _on_option_changed method starts timer."""
        with patch.object(self.webpage_page._options_changed_timer, "isActive", return_value=False):
            with patch.object(self.webpage_page._options_changed_timer, "start") as mock_start:
                self.webpage_page._on_option_changed()

                mock_start.assert_called_once()

    def test_get_options(self):
        """Test get_options method."""
        # Set some checkboxes
        self.webpage_page.use_proxy_cb.setChecked(True)
        self.webpage_page.ignore_ssl_cb.setChecked(False)
        self.webpage_page.download_images_cb.setChecked(True)
        self.webpage_page.filter_site_chrome_cb.setChecked(False)
        self.webpage_page.use_shared_browser_cb.setChecked(True)

        options = self.webpage_page.get_options()

        assert options["use_proxy"] is True
        assert options["ignore_ssl"] is False
        assert options["download_images"] is True
        assert options["filter_site_chrome"] is False
        assert options["use_shared_browser"] is True

    def test_set_options(self):
        """Test set_options method."""
        options = {
            "use_proxy": True,
            "ignore_ssl": False,
            "download_images": True,
            "filter_site_chrome": False,
            "use_shared_browser": True,
        }

        self.webpage_page.set_options(options)

        assert self.webpage_page.use_proxy_cb.isChecked() is True
        assert self.webpage_page.ignore_ssl_cb.isChecked() is False
        assert self.webpage_page.download_images_cb.isChecked() is True
        assert self.webpage_page.filter_site_chrome_cb.isChecked() is False
        assert self.webpage_page.use_shared_browser_cb.isChecked() is True

    def test_set_options_partial(self):
        """Test set_options method with partial options."""
        # Set initial state
        self.webpage_page.use_proxy_cb.setChecked(False)
        self.webpage_page.ignore_ssl_cb.setChecked(False)

        # Set only some options
        options = {"use_proxy": True}
        self.webpage_page.set_options(options)

        assert self.webpage_page.use_proxy_cb.isChecked() is True
        assert self.webpage_page.ignore_ssl_cb.isChecked() is False  # Should remain unchanged

    def test_set_options_invalid_keys(self):
        """Test set_options method with invalid keys."""
        # Set initial state
        self.webpage_page.use_proxy_cb.setChecked(False)

        # Set options with invalid key
        options = {"invalid_key": True, "use_proxy": True}
        self.webpage_page.set_options(options)

        assert self.webpage_page.use_proxy_cb.isChecked() is True
        # Should not raise exception for invalid keys

    def test_get_config(self):
        """Test get_config method."""
        # Set some checkboxes
        self.webpage_page.use_proxy_cb.setChecked(True)
        self.webpage_page.ignore_ssl_cb.setChecked(False)

        config = self.webpage_page.get_config()

        assert config["use_proxy"] is True
        assert config["ignore_ssl"] is False
        assert config["download_images"] is True  # Default value
        assert config["filter_site_chrome"] is True  # Default value
        assert config["use_shared_browser"] is True  # Default value

    def test_set_config(self):
        """Test set_config method."""
        config = {
            "use_proxy": True,
            "ignore_ssl": False,
            "download_images": True,
            "filter_site_chrome": False,
            "use_shared_browser": True,
        }

        self.webpage_page.set_config(config)

        assert self.webpage_page.use_proxy_cb.isChecked() is True
        assert self.webpage_page.ignore_ssl_cb.isChecked() is False
        assert self.webpage_page.download_images_cb.isChecked() is True
        assert self.webpage_page.filter_site_chrome_cb.isChecked() is False
        assert self.webpage_page.use_shared_browser_cb.isChecked() is True

    def test_retranslate_ui_with_translator(self):
        """Test retranslate_ui method with translator."""
        with patch.object(self.webpage_page.use_proxy_cb, "setText") as mock_proxy:
            with patch.object(self.webpage_page.ignore_ssl_cb, "setText") as mock_ssl:
                with patch.object(self.webpage_page.download_images_cb, "setText") as mock_images:
                    with patch.object(
                        self.webpage_page.filter_site_chrome_cb, "setText"
                    ) as mock_filter:
                        with patch.object(
                            self.webpage_page.use_shared_browser_cb, "setText"
                        ) as mock_browser:
                            self.webpage_page.retranslate_ui()

                            mock_proxy.assert_called_with("translated_use_proxy_checkbox")
                            mock_ssl.assert_called_with("translated_ignore_ssl_checkbox")
                            mock_images.assert_called_with("translated_download_images_checkbox")
                            mock_filter.assert_called_with("translated_filter_site_chrome_checkbox")
                            mock_browser.assert_called_with(
                                "translated_use_shared_browser_checkbox"
                            )

    def test_retranslate_ui_without_translator(self):
        """Test retranslate_ui method without translator."""
        self.webpage_page.translator = None

        # Should not raise exception
        self.webpage_page.retranslate_ui()

    def test_retranslate_ui_exception(self):
        """Test retranslate_ui method with exception."""
        # Mock translator to raise exception; implementation does not swallow
        self.webpage_page.translator.t = Mock(side_effect=Exception("Translation error"))
        with pytest.raises(Exception):
            self.webpage_page.retranslate_ui()

    def test_ui_elements_exist(self):
        """Test that all UI elements exist."""
        assert hasattr(self.webpage_page, "use_proxy_cb")
        assert hasattr(self.webpage_page, "ignore_ssl_cb")
        assert hasattr(self.webpage_page, "download_images_cb")
        assert hasattr(self.webpage_page, "filter_site_chrome_cb")
        assert hasattr(self.webpage_page, "use_shared_browser_cb")

    def test_checkbox_initial_states(self):
        """Test that checkboxes have correct initial states."""
        assert self.webpage_page.use_proxy_cb.isChecked() is False
        assert self.webpage_page.ignore_ssl_cb.isChecked() is False
        assert self.webpage_page.download_images_cb.isChecked() is True
        assert self.webpage_page.filter_site_chrome_cb.isChecked() is True
        assert self.webpage_page.use_shared_browser_cb.isChecked() is True
