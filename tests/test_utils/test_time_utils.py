"""
Tests for time utility functions.
"""

import pytest

from markdownall.utils.time_utils import human_readable_duration


class TestTimeUtils:
    """Test time utility functions."""

    def test_human_readable_duration_seconds_only(self):
        """Test human_readable_duration with seconds only."""
        result = human_readable_duration(45.123)
        assert result == "45.122 seconds"

    def test_human_readable_duration_minutes_and_seconds(self):
        """Test human_readable_duration with minutes and seconds."""
        result = human_readable_duration(125.456)
        assert result == "02 minutes05.456 seconds"

    def test_human_readable_duration_hours_minutes_seconds(self):
        """Test human_readable_duration with hours, minutes and seconds."""
        result = human_readable_duration(3661.789)
        assert result == "01 hours01 minutes01.789 seconds"

    def test_human_readable_duration_zero(self):
        """Test human_readable_duration with zero."""
        result = human_readable_duration(0.0)
        assert result == "00.000 seconds"

    def test_human_readable_duration_very_small(self):
        """Test human_readable_duration with very small value."""
        result = human_readable_duration(0.001)
        assert result == "00.001 seconds"

    def test_human_readable_duration_large_hours(self):
        """Test human_readable_duration with large hours."""
        result = human_readable_duration(7200.0)
        assert result == "02 hours00 minutes00.000 seconds"

    def test_human_readable_duration_59_minutes(self):
        """Test human_readable_duration with 59 minutes."""
        result = human_readable_duration(3540.0)
        assert result == "59 minutes00.000 seconds"

    def test_human_readable_duration_59_seconds(self):
        """Test human_readable_duration with 59 seconds."""
        result = human_readable_duration(59.999)
        assert result == "59.999 seconds"

    def test_human_readable_duration_negative(self):
        """Test human_readable_duration with negative value."""
        result = human_readable_duration(-10.5)
        # Negative values are handled by timedelta, which normalizes them
        assert "minutes" in result and "seconds" in result

    def test_human_readable_duration_very_large(self):
        """Test human_readable_duration with very large value."""
        result = human_readable_duration(86400.0)
        assert result == "24 hours00 minutes00.000 seconds"

    def test_human_readable_duration_fractional_hours(self):
        """Test human_readable_duration with fractional hours."""
        result = human_readable_duration(5400.0)  # 1.5 hours
        assert result == "01 hours30 minutes00.000 seconds"

    def test_human_readable_duration_precision(self):
        """Test human_readable_duration precision."""
        result = human_readable_duration(123.456789)
        assert result == "02 minutes03.456 seconds"

    def test_human_readable_duration_edge_cases(self):
        """Test human_readable_duration edge cases."""
        # Exactly 1 hour
        result = human_readable_duration(3600.0)
        assert result == "01 hours00 minutes00.000 seconds"

    def test_human_readable_duration_formatting(self):
        """Test human_readable_duration formatting."""
        result = human_readable_duration(3661.0)
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
        result = human_readable_duration(1.234)
        assert result == "01.234 seconds"

    def test_human_readable_duration_very_precise(self):
        """Test human_readable_duration with very precise value."""
        result = human_readable_duration(0.0001)
        assert result == "00.000 seconds"

    def test_human_readable_duration_integer_input(self):
        """Test human_readable_duration with integer input."""
        result = human_readable_duration(90)
        assert result == "01 minutes30.000 seconds"

    def test_human_readable_duration_string_conversion(self):
        """Test human_readable_duration with string input."""
        # The function expects float, not string
        with pytest.raises(TypeError):
            human_readable_duration("60.5")
