"""Test VersionCheckService functionality."""

import json
import os
from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest

from markdownall.services.version_check_service import VersionCheckService


class TestVersionCheckService:
    """Test VersionCheckService class."""

    def setup_method(self):
        """Setup test environment."""
        self.service = VersionCheckService()

    def test_get_latest_version_initial_state(self):
        """Test get_latest_version returns None initially."""
        assert self.service.get_latest_version() is None

    def test_get_latest_version_after_successful_check(self):
        """Test get_latest_version returns version after successful check."""
        # Mock successful API response
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_after_failed_check(self):
        """Test get_latest_version returns None after failed check."""
        with patch("urllib.request.urlopen", side_effect=URLError("Network error")):
            self.service.check_for_updates()

        assert self.service.get_latest_version() is None

    def test_get_last_error_initial_state(self):
        """Test get_last_error returns None initially."""
        assert self.service.get_last_error() is None

    def test_get_last_error_after_network_error(self):
        """Test get_last_error returns error message after network error."""
        with patch("urllib.request.urlopen", side_effect=URLError("Network error")):
            self.service.check_for_updates()

        assert self.service.get_last_error() == "<urlopen error Network error>"

    def test_get_last_error_after_json_error(self):
        """Test get_last_error returns error message after JSON decode error."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b"invalid json"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            self.service.check_for_updates()

        assert self.service.get_last_error() is not None
        assert "Expecting value: line 1 column 1 (char 0)" in str(self.service.get_last_error())

    def test_get_last_error_after_key_error(self):
        """Test get_last_error returns error message after KeyError."""
        mock_response_data = {
            "name": "Release 1.2.3",
            "body": "Release notes",
            # Missing "tag_name" key
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            self.service.check_for_updates()

        assert self.service.get_last_error() is not None

    def test_get_last_error_after_general_exception(self):
        """Test get_last_error returns error message after general exception."""
        with patch("urllib.request.urlopen", side_effect=Exception("General error")):
            self.service.check_for_updates()

        assert self.service.get_last_error() == "General error"

    def test_get_last_error_cleared_after_successful_check(self):
        """Test get_last_error is cleared after successful check."""
        # First, create an error
        with patch("urllib.request.urlopen", side_effect=URLError("Network error")):
            self.service.check_for_updates()

        assert self.service.get_last_error() is not None

        # Then, make a successful check
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_last_error() is None

    def test_get_latest_version_with_v_prefix(self):
        """Test get_latest_version strips 'v' prefix from tag_name."""
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_without_v_prefix(self):
        """Test get_latest_version works with tag_name without 'v' prefix."""
        mock_response_data = {"tag_name": "1.2.3", "name": "Release 1.2.3", "body": "Release notes"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_with_github_token(self):
        """Test get_latest_version works with GitHub token."""
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = Mock()
                mock_response.read.return_value = json.dumps(mock_response_data).encode()
                mock_urlopen.return_value.__enter__.return_value = mock_response

                with patch("markdownall.version.get_version", return_value="1.0.0"):
                    with patch("markdownall.version.compare_version", return_value=-1):
                        self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_with_gh_token(self):
        """Test get_latest_version works with GH_TOKEN."""
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch.dict(os.environ, {"GH_TOKEN": "test_token"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = Mock()
                mock_response.read.return_value = json.dumps(mock_response_data).encode()
                mock_urlopen.return_value.__enter__.return_value = mock_response

                with patch("markdownall.version.get_version", return_value="1.0.0"):
                    with patch("markdownall.version.compare_version", return_value=-1):
                        self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_priority_github_over_gh_token(self):
        """Test get_latest_version prioritizes GITHUB_TOKEN over GH_TOKEN."""
        mock_response_data = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch.dict(os.environ, {"GITHUB_TOKEN": "github_token", "GH_TOKEN": "gh_token"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = Mock()
                mock_response.read.return_value = json.dumps(mock_response_data).encode()
                mock_urlopen.return_value.__enter__.return_value = mock_response

                with patch("markdownall.version.get_version", return_value="1.0.0"):
                    with patch("markdownall.version.compare_version", return_value=-1):
                        self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

    def test_get_latest_version_multiple_checks(self):
        """Test get_latest_version updates with multiple checks."""
        # First check
        mock_response_data1 = {
            "tag_name": "v1.2.3",
            "name": "Release 1.2.3",
            "body": "Release notes",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data1).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.2.3"

        # Second check with different version
        mock_response_data2 = {
            "tag_name": "v1.3.0",
            "name": "Release 1.3.0",
            "body": "Release notes",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_response_data2).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with patch("markdownall.version.get_version", return_value="1.0.0"):
                with patch("markdownall.version.compare_version", return_value=-1):
                    self.service.check_for_updates()

        assert self.service.get_latest_version() == "1.3.0"

    def test_get_last_error_multiple_errors(self):
        """Test get_last_error updates with multiple errors."""
        # First error
        with patch("urllib.request.urlopen", side_effect=URLError("Network error")):
            self.service.check_for_updates()

        assert self.service.get_last_error() == "<urlopen error Network error>"

        # Second error
        with patch("urllib.request.urlopen", side_effect=Exception("General error")):
            self.service.check_for_updates()

        assert self.service.get_last_error() == "General error"
