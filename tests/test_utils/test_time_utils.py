"""
Tests for time utility functions.
"""

import pytest

from markdownall.utils.time_utils import human_readable_duration


class TestTimeUtils:
    """Test time utility functions."""

    def _get_mock_translator(self):
        """Get a mock translator for testing."""
        class MockTranslator:
            def t(self, key):
                translations = {
                    "time_unit_hours": "hours",
                    "time_unit_minutes": "minutes",
                    "time_unit_seconds": "seconds"
                }
                return translations.get(key, key)
        return MockTranslator()

    def test_human_readable_duration_seconds_only(self):
        """Test human_readable_duration with seconds only."""
        translator = self._get_mock_translator()
        result = human_readable_duration(45.123, translator)
        assert result == "45.122 seconds"

    def test_human_readable_duration_minutes_and_seconds(self):
        """Test human_readable_duration with minutes and seconds."""
        translator = self._get_mock_translator()
        result = human_readable_duration(125.456, translator)
        assert result == "02 minutes 05.456 seconds"

    def test_human_readable_duration_hours_minutes_seconds(self):
        """Test human_readable_duration with hours, minutes and seconds."""
        translator = self._get_mock_translator()
        result = human_readable_duration(3661.789, translator)
        assert result == "01 hours 01 minutes 01.789 seconds"

    def test_human_readable_duration_zero(self):
        """Test human_readable_duration with zero."""
        translator = self._get_mock_translator()
        result = human_readable_duration(0.0, translator)
        assert result == "00.000 seconds"

    def test_human_readable_duration_very_small(self):
        """Test human_readable_duration with very small value."""
        translator = self._get_mock_translator()
        result = human_readable_duration(0.001, translator)
        assert result == "00.001 seconds"

    def test_human_readable_duration_large_hours(self):
        """Test human_readable_duration with large hours."""
        translator = self._get_mock_translator()
        result = human_readable_duration(7200.0, translator)
        assert result == "02 hours 00 minutes 00.000 seconds"

    def test_human_readable_duration_59_minutes(self):
        """Test human_readable_duration with 59 minutes."""
        translator = self._get_mock_translator()
        result = human_readable_duration(3540.0, translator)
        assert result == "59 minutes 00.000 seconds"

    def test_human_readable_duration_59_seconds(self):
        """Test human_readable_duration with 59 seconds."""
        translator = self._get_mock_translator()
        result = human_readable_duration(59.999, translator)
        assert result == "59.999 seconds"

    def test_human_readable_duration_negative(self):
        """Test human_readable_duration with negative value."""
        translator = self._get_mock_translator()
        result = human_readable_duration(-10.5, translator)
        # Negative values are handled by timedelta, which normalizes them
        assert "minutes" in result and "seconds" in result

    def test_human_readable_duration_very_large(self):
        """Test human_readable_duration with very large value."""
        translator = self._get_mock_translator()
        result = human_readable_duration(86400.0, translator)
        assert result == "24 hours 00 minutes 00.000 seconds"

    def test_human_readable_duration_fractional_hours(self):
        """Test human_readable_duration with fractional hours."""
        translator = self._get_mock_translator()
        result = human_readable_duration(5400.0, translator)  # 1.5 hours
        assert result == "01 hours 30 minutes 00.000 seconds"

    def test_human_readable_duration_precision(self):
        """Test human_readable_duration precision."""
        translator = self._get_mock_translator()
        result = human_readable_duration(123.456789, translator)
        assert result == "02 minutes 03.456 seconds"

    def test_human_readable_duration_edge_cases(self):
        """Test human_readable_duration edge cases."""
        # Exactly 1 hour
        translator = self._get_mock_translator()
        result = human_readable_duration(3600.0, translator)
        assert result == "01 hours 00 minutes 00.000 seconds"

    def test_human_readable_duration_formatting(self):
        """Test human_readable_duration formatting."""
        translator = self._get_mock_translator()
        result = human_readable_duration(3661.0, translator)
        parts = result.split()

        # Check that hours, minutes, seconds are present
        assert "hours" in result
        assert "minutes" in result
        assert "seconds" in result

        # Check format: XX hoursXX minutesXX.XXX seconds
        assert result.count("hours") == 1
        assert result.count("minutes") == 1
        assert result.count("seconds") == 1

    def test_human_readable_duration_milliseconds(self):
        """Test human_readable_duration with milliseconds."""
        translator = self._get_mock_translator()
        result = human_readable_duration(1.234, translator)
        assert result == "01.234 seconds"

    def test_human_readable_duration_very_precise(self):
        """Test human_readable_duration with very precise value."""
        translator = self._get_mock_translator()
        result = human_readable_duration(0.0001, translator)
        assert result == "00.000 seconds"

    def test_human_readable_duration_integer_input(self):
        """Test human_readable_duration with integer input."""
        translator = self._get_mock_translator()
        result = human_readable_duration(90, translator)
        assert result == "01 minutes 30.000 seconds"

    def test_human_readable_duration_string_conversion(self):
        """Test human_readable_duration with string input."""
        translator = self._get_mock_translator()
        # The function expects float, not string
        with pytest.raises(TypeError):
            human_readable_duration("60.5", translator)

    def test_human_readable_duration_with_translator(self):
        """Test human_readable_duration with translator."""
        # Mock translator for Chinese
        class MockChineseTranslator:
            def t(self, key):
                translations = {
                    "time_unit_hours": "小时",
                    "time_unit_minutes": "分钟",
                    "time_unit_seconds": "秒"
                }
                return translations.get(key, key)
        
        translator = MockChineseTranslator()
        result = human_readable_duration(182.758, translator)
        assert result == "03 分钟 02.758 秒"
        
        # Test with hours
        result = human_readable_duration(3661.789, translator)
        assert result == "01 小时 01 分钟 01.789 秒"
