from unittest.mock import MagicMock, patch
from models.memory import History, HistoryEvent
from utils.alexa import (
    get_base_services,
    get_device_timezone,
    build_extraction_service,
    parse_history,
    update_history,
)
import utils.alexa as alexa_module


def _event(access_token: str = "", with_system: bool = False) -> dict:
    event: dict = {
        "session": {"user": {"userId": "test_user"}, "attributes": {}},
        "request": {"type": "IntentRequest"},
        "context": {"System": {"user": {}}},
    }
    if access_token:
        event["context"]["System"]["user"]["accessToken"] = access_token
    if with_system:
        event["context"]["System"].update(
            {
                "apiEndpoint": "https://api.eu.amazonalexa.com",
                "apiAccessToken": "fake_token",
                "device": {"deviceId": "device_123"},
            }
        )
    return event


class TestGetDeviceTimezone:
    def test_returns_utc_when_missing_fields(self):
        assert get_device_timezone(_event()) == "UTC"

    @patch("utils.alexa.urllib.request.urlopen")
    def test_returns_timezone_from_api(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'"Europe/Rome"'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert get_device_timezone(_event(with_system=True)) == "Europe/Rome"

    @patch("utils.alexa.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_returns_utc_on_error(self, mock_urlopen):
        assert get_device_timezone(_event(with_system=True)) == "UTC"


class TestBuildExtractionService:
    @patch("utils.alexa.CalendarService")
    @patch("utils.alexa.get_device_timezone", return_value="Europe/Rome")
    @patch("utils.alexa.get_base_services")
    def test_with_access_token(self, mock_base, mock_tz, mock_cal):
        mock_base.return_value = (MagicMock(), MagicMock())
        service = build_extraction_service(_event(access_token="fake_token"))
        mock_cal.assert_called_once_with("fake_token", "Europe/Rome")
        assert service.calendar_service is not None

    @patch("utils.alexa.get_base_services")
    def test_without_access_token(self, mock_base):
        mock_base.return_value = (MagicMock(), MagicMock())
        service = build_extraction_service(_event())
        assert service.calendar_service is None


class TestGetBaseServices:
    @patch("utils.alexa.LlmService")
    @patch("utils.alexa.Groq")
    @patch("utils.alexa.boto3")
    def test_creates_services_once(self, mock_boto3, mock_groq, mock_llm, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake_key")
        alexa_module._memory_service = None
        alexa_module._llm_service = None

        mem1, llm1 = get_base_services()
        mem2, llm2 = get_base_services()

        assert mem1 is mem2
        assert llm1 is llm2

        alexa_module._memory_service = None
        alexa_module._llm_service = None


class TestParseHistory:
    def test_empty_session(self):
        event = _event()
        history = parse_history(event)
        assert history.exchanges == []

    def test_existing_history(self):
        event = _event()
        event["session"]["attributes"] = {
            "history": [
                {"user_request": "hello", "agent_reply": "hi"},
                {"user_request": "how are you", "agent_reply": "good"},
            ]
        }
        history = parse_history(event)
        assert len(history.exchanges) == 2
        assert history.exchanges[0].user_request == "hello"


class TestUpdateHistory:
    def test_appends_and_returns_attrs(self):
        history = History(exchanges=[])
        attrs = update_history(history, "hello", "hi there")
        assert len(attrs["history"]) == 1
        assert attrs["history"][0]["user_request"] == "hello"
        assert attrs["history"][0]["agent_reply"] == "hi there"

    def test_caps_at_20(self):
        events = [HistoryEvent(user_request=f"q{i}", agent_reply=f"a{i}") for i in range(20)]
        history = History(exchanges=events)
        attrs = update_history(history, "new", "reply")
        assert len(attrs["history"]) == 20
        assert attrs["history"][-1]["user_request"] == "new"
        assert attrs["history"][0]["user_request"] == "q1"
