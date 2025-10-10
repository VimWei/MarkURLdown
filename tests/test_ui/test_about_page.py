"""Test AboutPage functionality."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from markdownall.ui.pyside.pages.about_page import AboutPage, VersionCheckThread


class TestVersionCheckThread:
    """Test VersionCheckThread class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_init(self):
        """Test VersionCheckThread initialization."""
        thread = VersionCheckThread()
        assert isinstance(thread, QThread)
        assert hasattr(thread, "update_available")

    def test_run(self):
        """Test VersionCheckThread run method."""
        thread = VersionCheckThread()
        # The run method is currently empty (TODO implementation)
        # Should not raise any exception
        thread.run()

    def test_update_available_signal(self):
        """Test VersionCheckThread update_available signal."""
        thread = VersionCheckThread()
        assert hasattr(thread, "update_available")
        assert thread.update_available is not None


class TestAboutPage:
    """Test AboutPage class."""

    def setup_method(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        self.mock_translator = Mock()
        self.mock_translator.t = Mock(side_effect=lambda key, **kwargs: f"translated_{key}")

        self.about_page = AboutPage(translator=self.mock_translator)

    def test_check_for_updates_already_running(self):
        """Test check_for_updates method when already checking."""
        # Mock an already running thread
        mock_thread = Mock()
        mock_thread.isRunning.return_value = True
        self.about_page.version_thread = mock_thread

        # Should return early without starting new thread
        self.about_page.check_for_updates()

        # Verify no new thread was created
        assert self.about_page.version_thread == mock_thread

    def test_check_for_updates_with_translator(self):
        """Test check_for_updates method with translator."""
        self.about_page.version_thread = None

        with patch(
            "markdownall.ui.pyside.pages.about_page.VersionCheckThread"
        ) as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            # Patch UI setters to allow call assertions
            with (
                patch.object(self.about_page.update_status_label, "setText") as mock_set_text,
                patch.object(self.about_page.check_updates_btn, "setEnabled") as mock_set_enabled,
                patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text,
            ):
                self.about_page.check_for_updates()

                # Verify UI updates
                mock_set_text.assert_called_with("translated_about_checking")
                mock_set_enabled.assert_called_with(False)
                mock_btn_text.assert_called_with("translated_about_checking")

            # Verify thread creation and connection if created
            if mock_thread_class.called:
                mock_thread.update_available.connect.assert_called_once_with(
                    self.about_page.on_update_check_complete
                )
                mock_thread.finished.connect.assert_called_once_with(
                    self.about_page.on_version_thread_finished
                )
                mock_thread.start.assert_called_once()

    def test_check_for_updates_without_translator(self):
        """Test check_for_updates method without translator."""
        self.about_page.translator = None
        self.about_page.version_thread = None

        with patch(
            "markdownall.ui.pyside.pages.about_page.VersionCheckThread"
        ) as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            # Patch UI setters for assertions
            with (
                patch.object(self.about_page.update_status_label, "setText") as mock_set_text,
                patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text,
            ):
                self.about_page.check_for_updates()

                # Verify UI updates with default text
                mock_set_text.assert_called_with("Checking for updates...")
                mock_btn_text.assert_called_with("Checking...")

    def test_on_update_check_complete_with_translator_up_to_date(self):
        """Test on_update_check_complete method with translator and up-to-date message."""
        with patch.object(self.about_page.update_status_label, "setText") as mock_set_text:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text:
                self.about_page.on_update_check_complete(
                    True, "You are using the latest version.", "1.0.0"
                )

                mock_set_text.assert_called_with("translated_about_latest_version")
                mock_btn_text.assert_called_with("translated_about_check_again")

    def test_on_update_check_complete_with_translator_custom_message(self):
        """Test on_update_check_complete method with translator and custom message."""
        with patch.object(self.about_page.update_status_label, "setText") as mock_set_text:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text:
                self.about_page.on_update_check_complete(
                    False, "New version 2.0.0 available", "2.0.0"
                )

                mock_set_text.assert_called_with("translated_about_new_version_available")
                mock_btn_text.assert_called_with("translated_about_check_again")

    def test_on_update_check_complete_without_translator(self):
        """Test on_update_check_complete method without translator."""
        self.about_page.translator = None

        with patch.object(self.about_page.update_status_label, "setText") as mock_set_text:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text:
                self.about_page.on_update_check_complete(
                    True, "You are using the latest version.", "1.0.0"
                )

                mock_set_text.assert_called_with("You are using the latest version.")
                mock_btn_text.assert_called_with("Check Again")

    def test_on_update_check_complete_exception(self):
        """Test on_update_check_complete method with exception."""

        # Mock translator to raise for status text but succeed for button text
        def t_side_effect(key, **kwargs):
            if key == "about_latest_version":
                raise Exception("Translation error")
            return f"translated_{key}"

        self.about_page.translator.t = Mock(side_effect=t_side_effect)

        with patch.object(self.about_page.update_status_label, "setText") as mock_set_text:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_btn_text:
                self.about_page.on_update_check_complete(
                    True, "Current version is up to date", "1.0.0"
                )

                # Should fall back to raw message; button still uses translator
                mock_set_text.assert_called_with("Current version is up to date")
                mock_btn_text.assert_called_with("translated_about_check_again")

    def test_on_version_thread_finished_with_translator(self):
        """Test on_version_thread_finished method with translator."""
        mock_thread = Mock()
        self.about_page.version_thread = mock_thread

        with patch.object(self.about_page.check_updates_btn, "setEnabled") as mock_enabled:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_text:
                self.about_page.on_version_thread_finished()

                mock_enabled.assert_called_with(True)
                mock_text.assert_called_with("translated_about_check_again")
                mock_thread.deleteLater.assert_called_once()
                assert self.about_page.version_thread is None

    def test_on_version_thread_finished_without_translator(self):
        """Test on_version_thread_finished method without translator."""
        self.about_page.translator = None
        mock_thread = Mock()
        self.about_page.version_thread = mock_thread

        with patch.object(self.about_page.check_updates_btn, "setEnabled") as mock_enabled:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_text:
                self.about_page.on_version_thread_finished()

                mock_enabled.assert_called_with(True)
                mock_text.assert_called_with("Check Again")
                mock_thread.deleteLater.assert_called_once()
                assert self.about_page.version_thread is None

    def test_on_version_thread_finished_no_thread(self):
        """Test on_version_thread_finished method with no thread."""
        self.about_page.version_thread = None

        with patch.object(self.about_page.check_updates_btn, "setEnabled") as mock_enabled:
            with patch.object(self.about_page.check_updates_btn, "setText") as mock_text:
                self.about_page.on_version_thread_finished()

                mock_enabled.assert_called_with(True)
                mock_text.assert_called_with("translated_about_check_again")
                assert self.about_page.version_thread is None

    def test_retranslate_ui_with_translator(self):
        """Test retranslate_ui method with translator."""
        with patch.object(self.about_page._lbl_home, "setText") as mock_home:
            with patch.object(self.about_page._lbl_update, "setText") as mock_update:
                with patch.object(self.about_page.update_status_label, "setText") as mock_status:
                    with patch.object(self.about_page.check_updates_btn, "setText") as mock_btn:
                        self.about_page.retranslate_ui()

                        mock_home.assert_called_with("translated_about_homepage")
                        mock_update.assert_called_with("translated_about_updates")
                        mock_status.assert_called_with("translated_about_click_to_check")
                        mock_btn.assert_called_with("translated_about_check_updates")

    def test_retranslate_ui_without_translator(self):
        """Test retranslate_ui method without translator."""
        self.about_page.translator = None

        # Should not raise exception
        self.about_page.retranslate_ui()

    def test_retranslate_ui_exception(self):
        """Test retranslate_ui method with exception."""
        # Mock translator to raise exception
        self.about_page.translator.t = Mock(side_effect=Exception("Translation error"))

        # Should not raise exception
        self.about_page.retranslate_ui()

    def test_initialization(self):
        """Test AboutPage initialization."""
        assert self.about_page.translator == self.mock_translator
        assert self.about_page.version_thread is None
        assert hasattr(self.about_page, "checkUpdatesRequested")
        assert hasattr(self.about_page, "openHomepageRequested")

    def test_initialization_without_translator(self):
        """Test AboutPage initialization without translator."""
        page = AboutPage(translator=None)
        assert page.translator is None
        assert page.version_thread is None

    def test_signal_connections(self):
        """Test that signals are properly connected."""
        # Test check updates button
        with patch.object(self.about_page, "check_for_updates") as mock_check:
            self.about_page.check_updates_btn.clicked.emit()
            mock_check.assert_called_once()

        # Ensure signal exists (click on link widget is not programmatically tested here)
        assert hasattr(self.about_page, "openHomepageRequested")
