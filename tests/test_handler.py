from unittest.mock import patch
from handler import lambda_handler, LAUNCH_MSG, HELP_MSG, FALLBACK_MSG


def _alexa_event(intent: str, text: str = "", user_id: str = "test_user", access_token: str = "") -> dict:
    event: dict = {
        "session": {"user": {"userId": user_id}, "attributes": {}},
        "request": {},
        "context": {"System": {"user": {}}},
    }
    if access_token:
        event["context"]["System"]["user"]["accessToken"] = access_token
    if intent == "LaunchRequest":
        event["request"] = {"type": "LaunchRequest"}
    elif intent == "SessionEndedRequest":
        event["request"] = {"type": "SessionEndedRequest"}
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
        assert result["response"]["reprompt"]["outputSpeech"]["text"] == "I'm listening."

    @patch("handler.build_extraction_service")
    def test_log_activity_intent(self, mock_build):
        mock_build.return_value.process.return_value = "Got it!"
        result = lambda_handler(_alexa_event("LogActivityIntent", "I work at Amazon"), None)
        assert result["response"]["outputSpeech"]["text"] == "Got it!"
        assert "sessionAttributes" in result
        assert "history" in result["sessionAttributes"]

    @patch("handler.build_extraction_service")
    def test_session_history_accumulates(self, mock_build):
        mock_build.return_value.process.return_value = "Noted!"
        event = _alexa_event("LogActivityIntent", "I work at Amazon")
        event["session"]["attributes"] = {"history": [{"user_request": "hello", "agent_reply": "hi there"}]}
        result = lambda_handler(event, None)
        history = result["sessionAttributes"]["history"]
        assert len(history) == 2
        assert history[0]["user_request"] == "hello"
        assert history[1]["user_request"] == "I work at Amazon"

    def test_session_ended_request(self):
        result = lambda_handler(_alexa_event("SessionEndedRequest"), None)
        assert result["response"]["shouldEndSession"] is True

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
            "session": {"user": {"userId": "test_user"}, "attributes": {}},
            "request": {"type": "SomeUnknownType"},
            "context": {"System": {"user": {}}},
        }
        result = lambda_handler(event, None)
        assert "didn't catch" in result["response"]["outputSpeech"]["text"].lower()
        assert "reprompt" in result["response"]

    @patch("handler.build_extraction_service")
    def test_error_handling(self, mock_build):
        mock_build.return_value.process.side_effect = Exception("boom")
        result = lambda_handler(_alexa_event("LogActivityIntent", "test"), None)
        assert "went wrong" in result["response"]["outputSpeech"]["text"].lower()
        assert "reprompt" in result["response"]
