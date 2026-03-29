from unittest.mock import MagicMock, patch
from models.calendar import CalendarEvent, CalendarEventResult
from services.calendar_service import CalendarService


@patch("services.calendar_service.build")
@patch("services.calendar_service.Credentials")
class TestCalendarService:
    def test_create_event(self, mock_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "summary": "Trip to China",
            "start": {"date": "2026-10-15"},
        }

        service = CalendarService("fake_token")
        event = CalendarEvent(summary="Trip to China", date="2026-10-15", duration_hours=24)
        result = service.create_event(event)

        assert result.summary == "Trip to China"
        assert result.date == "2026-10-15"
        mock_service.events.return_value.insert.assert_called_once()

    def test_create_timed_event(self, mock_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "summary": "Meeting",
            "start": {"dateTime": "2026-10-15T10:00:00"},
        }

        service = CalendarService("fake_token")
        event = CalendarEvent(summary="Meeting", date="2026-10-15", duration_hours=1)
        result = service.create_event(event)

        assert result.summary == "Meeting"
        body = mock_service.events.return_value.insert.call_args[1]["body"]
        assert "dateTime" in body["start"]

    def test_get_events(self, mock_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": [
                {"summary": "Standup", "start": {"dateTime": "2026-03-30T09:00:00Z"}},
                {"summary": "Dentist", "start": {"date": "2026-04-01"}},
            ]
        }

        service = CalendarService("fake_token")
        events = service.get_events(days=7)

        assert len(events) == 2
        assert events[0].summary == "Standup"
        assert events[1].summary == "Dentist"
        assert events[1].date == "2026-04-01"

    def test_get_events_empty(self, mock_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}

        service = CalendarService("fake_token")
        events = service.get_events()

        assert events == []
