from unittest.mock import MagicMock, patch
from handler import lambda_handler, _get_extraction_service, LAUNCH_MSG, HELP_MSG, FALLBACK_MSG
import handler


def _alexa_event(intent: str, text: str = "", user_id: str = "test_user") -> dict:
    event: dict = {
        "session": {"user": {"userId": user_id}},
        "request": {},
    }
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

    @patch("handler._get_extraction_service")
    def test_log_activity_intent(self, mock_get_service):
        mock_get_service.return_value.process.return_value = "Got it!"
        result = lambda_handler(_alexa_event("LogActivityIntent", "I work at Amazon"), None)
        assert result["response"]["outputSpeech"]["text"] == "Got it!"
        mock_get_service.return_value.process.assert_called_once_with("test_user", "I work at Amazon")

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
        }
        result = lambda_handler(event, None)
        assert "didn't catch" in result["response"]["outputSpeech"]["text"].lower()

    @patch("handler._get_extraction_service")
    def test_error_handling(self, mock_get_service):
        mock_get_service.return_value.process.side_effect = Exception("boom")
        result = lambda_handler(_alexa_event("LogActivityIntent", "test"), None)
        assert "went wrong" in result["response"]["outputSpeech"]["text"].lower()


class TestGetExtractionService:
    @patch("handler.ExtractionService")
    @patch("handler.LlmService")
    @patch("handler.MemoryService")
    @patch("handler.Groq")
    @patch("handler.boto3")
    def test_creates_service_once(self, mock_boto3, mock_groq, mock_memory, mock_llm, mock_extraction, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake_key")
        handler._extraction_service = None

        result1 = _get_extraction_service()
        result2 = _get_extraction_service()

        assert result1 is result2
        mock_extraction.assert_called_once()

        handler._extraction_service = None
