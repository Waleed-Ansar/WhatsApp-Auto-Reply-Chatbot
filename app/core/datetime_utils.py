from datetime import datetime
from dateparser.search import search_dates


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