"""Date helpers. `logged_date` is always a *local* calendar date."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def today_for(tz_name: str | None) -> date:
    """The user's current local date. Falls back to UTC on a bad/empty tz."""
    try:
        tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    except (KeyError, ValueError, OSError):  # ZoneInfoNotFoundError subclasses KeyError
        tz = timezone.utc
    return datetime.now(tz).date()


def daterange(start: date, end: date) -> Iterator[date]:
    """Every date from start to end, inclusive."""
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)