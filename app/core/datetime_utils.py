from datetime import datetime
from dateparser.search import search_dates
from dateutil import parser


def has_date_and_time(text):
    """Check if text contains both date and time information"""
    parsed = search_dates(text)
    if parsed:
        for _, dt in parsed:
            if dt.time() != dt.replace(hour=0, minute=0, second=0).time():
                return True
    return False

def has_time_info(dt: datetime) -> bool:
    """Check if datetime object has time information (not just date)"""
    return not (dt.hour == 0 and dt.minute == 0 and dt.second == 0)

def normalize_appointment_times(start_time, end_time):
    """
    Accept datetime objects or common date-time strings and return
    normalized startTime and endTime strings for an API request.

    Examples accepted:
        2026-10-29 09:00
        2026-10-29T09:00:00
        29/10/2026 9:00 AM
        October 29, 2026 9:00 AM
        2026-10-29T09:00:00+05:00
    """

    def parse_datetime(value, field_name):
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str) and value.strip():
            dt = parser.parse(
                value.strip(),
                dayfirst=True,
                yearfirst=True,
                fuzzy=False,
            )
        else:
            raise ValueError(
                f"{field_name} must be a valid date-time string "
                "or datetime object."
            )

        return dt.replace(microsecond=0)

    start_dt = parse_datetime(start_time, "start_time")
    end_dt = parse_datetime(end_time, "end_time")

    # Do not silently mix timezone-aware and timezone-naive values.
    if (start_dt.utcoffset() is None) != (end_dt.utcoffset() is None):
        raise ValueError(
            "Start and end times must both include a timezone "
            "or both omit it."
        )

    if end_dt <= start_dt:
        raise ValueError("end_time must be later than start_time.")

    start_time = start_dt.isoformat(timespec="seconds")
    end_time = end_dt.isoformat(timespec="seconds")

    return start_time, end_time