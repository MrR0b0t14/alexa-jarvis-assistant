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
        start = datetime.fromisoformat(event.date)
        end = start + timedelta(hours=event.duration_hours)

        body: dict[str, Any] = {
            "summary": event.summary,
            "description": event.description,
        }

        if event.is_all_day:
            body["start"] = {"date": event.date}
            body["end"] = {"date": (start + timedelta(days=1)).strftime("%Y-%m-%d")}
        else:
            body["start"] = {"dateTime": start.isoformat(), "timeZone": "UTC"}
            body["end"] = {"dateTime": end.isoformat(), "timeZone": "UTC"}

        result = self.service.events().insert(calendarId="primary", body=body).execute()
        logger.info("Created event: %s on %s", event.summary, event.date)
        return CalendarEventResult.from_google(result)

    def get_events(self, days: int = 7) -> list[CalendarEventResult]:
        """Retrieves upcoming calendar events.

        Args:
            days: Number of days to look ahead (default 7).

        Returns:
            A list of ``CalendarEventResult`` instances.
        """
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()

        result = self.service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = [CalendarEventResult.from_google(e) for e in result.get("items", [])]
        logger.info("Found %d events in next %d days", len(events), days)
        return events
