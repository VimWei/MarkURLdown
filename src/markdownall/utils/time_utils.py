"""时间处理工具函数"""

from datetime import timedelta


def human_readable_duration(seconds: float, translator) -> str:
    """Convert seconds to human readable duration string with proper spacing.

    Args:
        seconds: Duration in seconds
        translator: Translator object for localization

    Returns:
        Human readable duration string with proper spacing (e.g., "03 minutes 02.758 seconds")
    """
    time_delta = timedelta(seconds=seconds)
    hours, remainder = divmod(time_delta.total_seconds(), 3600)
    minutes, int_seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(hours) * 3600 - int(minutes) * 60 - int(int_seconds)) * 1000)

    # Get time units from translator
    hour_unit = translator.t("time_unit_hours")
    minute_unit = translator.t("time_unit_minutes")
    second_unit = translator.t("time_unit_seconds")

    parts: list[str] = []
    if int(hours) > 0:
        parts.append(f"{int(hours):02d} {hour_unit}")
    if int(minutes) > 0 or int(hours) > 0:
        parts.append(f"{int(minutes):02d} {minute_unit}")
    parts.append(f"{int(int_seconds):02d}.{milliseconds:03d} {second_unit}")

    return " ".join(parts)
