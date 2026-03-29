from unittest.mock import MagicMock, patch
from handler import lambda_handler, _get_base_services, _build_extraction_service, LAUNCH_MSG, HELP_MSG, FALLBACK_MSG
import handler


def _alexa_event(intent: str, text: str = "", user_id: str = "test_user", access_token: str = "") -> dict:
    event: dict = {
        "session": {"user": {"userId": user_id}},
        "request": {},
        "context": {"System": {"user": {}}},
    }
    if access_token:
        event["context"]["System"]["user"]["accessToken"] = access_token
    if intent == "LaunchRequest":
        event["request"] = {"type": "LaunchRequest"}
    else:
        event["request"] = {
            "type": "IntentRequest",
            "intent": {
                "name": intent,
                "slots": {"freeText": {"value": text}},
            },
        }
    return event


class TestLambdaHandler:
    def test_launch_request(self):
        result = lambda_handler(_alexa_event("LaunchRequest"), None)
        assert result["response"]["outputSpeech"]["text"] == LAUNCH_MSG
        assert result["response"]["shouldEndSession"] is False

    @patch("handler._build_extraction_service")
    def test_log_activity_intent(self, mock_build):
        mock_build.return_value.process.return_value = "Got it!"
        result = lambda_handler(_alexa_event("LogActivityIntent", "I work at Amazon"), None)
        assert result["response"]["outputSpeech"]["text"] == "Got it!"
        mock_build.return_value.process.assert_called_once_with("test_user", "I work at Amazon")

    def test_stop_intent(self):
        result = lambda_handler(_alexa_event("AMAZON.StopIntent"), None)
        assert result["response"]["shouldEndSession"] is True

    def test_cancel_intent(self):
        result = lambda_handler(_alexa_event("AMAZON.CancelIntent"), None)
        assert result["response"]["shouldEndSession"] is True

    def test_help_intent(self):
        result = lambda_handler(_alexa_event("AMAZON.HelpIntent"), None)
        assert result["response"]["outputSpeech"]["text"] == HELP_MSG

    def test_fallback_intent(self):
        result = lambda_handler(_alexa_event("AMAZON.FallbackIntent"), None)
        assert result["response"]["outputSpeech"]["text"] == FALLBACK_MSG

    def test_unknown_request_type(self):
        event = {
            "session": {"user": {"userId": "test_user"}},
            "request": {"type": "SomeUnknownType"},
            "context": {"System": {"user": {}}},
        }
        result = lambda_handler(event, None)
        assert "didn't catch" in result["response"]["outputSpeech"]["text"].lower()

    @patch("handler._build_extraction_service")
    def test_error_handling(self, mock_build):
        mock_build.return_value.process.side_effect = Exception("boom")
        result = lambda_handler(_alexa_event("LogActivityIntent", "test"), None)
        assert "went wrong" in result["response"]["outputSpeech"]["text"].lower()


class TestBuildExtractionService:
    @patch("handler.CalendarService")
    @patch("handler._get_base_services")
    def test_with_access_token(self, mock_base, mock_cal):
        mock_base.return_value = (MagicMock(), MagicMock())
        event = _alexa_event("LogActivityIntent", access_token="fake_token")
        service = _build_extraction_service(event)
        mock_cal.assert_called_once_with("fake_token")
        assert service.calendar_service is not None

    @patch("handler._get_base_services")
    def test_without_access_token(self, mock_base):
        mock_base.return_value = (MagicMock(), MagicMock())
        event = _alexa_event("LogActivityIntent")
        service = _build_extraction_service(event)
        assert service.calendar_service is None


class TestGetBaseServices:
    @patch("handler.LlmService")
    @patch("handler.Groq")
    @patch("handler.boto3")
    def test_creates_services_once(self, mock_boto3, mock_groq, mock_llm, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake_key")
        handler._memory_service = None
        handler._llm_service = None

        mem1, llm1 = _get_base_services()
        mem2, llm2 = _get_base_services()

        assert mem1 is mem2
        assert llm1 is llm2

        handler._memory_service = None
        handler._llm_service = None
