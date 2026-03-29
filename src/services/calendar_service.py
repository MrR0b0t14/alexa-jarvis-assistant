"""Google Calendar API integration."""

from typing import Any
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from models.calendar import CalendarEvent, CalendarEventResult
from config.logger import get_logger

logger = get_logger(__name__)


class CalendarService:
    """Handles Google Calendar API operations using an OAuth access token.

    Args:
        access_token: The OAuth2 access token from Alexa Account Linking.
    """

    def __init__(self, access_token: str) -> None:
        credentials = Credentials(token=access_token)
        self.service = build("calendar", "v3", credentials=credentials)

    def create_event(self, event: CalendarEvent) -> CalendarEventResult:
        """Creates a calendar event.

        Args:
            event: The event to create.

        Returns:
            The created event as a ``CalendarEventResult``.
        """
        body: dict[str, Any] = {
            "summary": event.summary,
            "description": event.description,
        }

        if event.is_all_day:
            start = datetime.fromisoformat(event.date)
            body["start"] = {"date": event.date}
            body["end"] = {"date": (start + timedelta(days=1)).strftime("%Y-%m-%d")}
        else:
            start_dt = datetime.fromisoformat(f"{event.date}T{event.time}:00")
            end_dt = start_dt + timedelta(hours=event.duration_hours)
            body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
            body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}

        result = self.service.events().insert(calendarId="primary", body=body).execute()
        logger.info("Created event: %s on %s %s", event.summary, event.date, event.time or "all-day")
        return CalendarEventResult.from_google(result)

    def get_events(self, start_date: str = "", end_date: str = "") -> list[CalendarEventResult]:
        """Retrieves calendar events within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. Defaults to now.
            end_date: End date in YYYY-MM-DD format. Defaults to 7 days from start.

        Returns:
            A list of ``CalendarEventResult`` instances.
        """
        if start_date:
            time_min = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc).isoformat()
        else:
            time_min = datetime.now(timezone.utc).isoformat()

        if end_date:
            time_max = (datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)).isoformat()
        else:
            time_max = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        result = self.service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = [CalendarEventResult.from_google(e) for e in result.get("items", [])]
        logger.info("Found %d events between %s and %s", len(events), start_date or "now", end_date or "+7d")
        return events
