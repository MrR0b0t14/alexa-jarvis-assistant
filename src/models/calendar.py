"""Data models for Google Calendar integration."""

from typing import Any
from pydantic import BaseModel


class CalendarEvent(BaseModel):
    """A Google Calendar event to create.

    Attributes:
        summary: Event title.
        date: Date string in YYYY-MM-DD format.
        time: Time string in HH:MM 24h format. Empty for all-day events.
        description: Optional event description.
        duration_hours: Duration in hours (default 1). Use 24 for all-day events.
    """

    summary: str
    date: str
    time: str = ""
    description: str = ""
    duration_hours: int = 1

    @property
    def is_all_day(self) -> bool:
        """Returns True if this is an all-day event."""
        return self.duration_hours >= 24


class CalendarEventResult(BaseModel):
    """A calendar event returned from a query.

    Attributes:
        summary: Event title.
        date: Start date (YYYY-MM-DD).
    """

    summary: str
    date: str

    @classmethod
    def from_google(cls, event: dict[str, Any]) -> "CalendarEventResult":
        """Parses a Google Calendar API event resource.

        Args:
            event: A raw event dict from the Google Calendar API.

        Returns:
            A ``CalendarEventResult`` instance.
        """
        start = event.get("start", {})
        date = start.get("date") or start.get("dateTime", "")[:10]
        return cls(
            summary=event.get("summary", "Untitled"),
            date=date,
        )
