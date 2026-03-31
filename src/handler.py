"""Lambda entry point for the Alexa Jarvis Assistant."""

from typing import Any
from utils.response import build_response
from utils.alexa import build_extraction_service, parse_history, update_history
from config.logger import get_logger

logger = get_logger(__name__)

LAUNCH_MSG = (
    "Hey, I'm Jarvis, your personal AI assistant with memory. "
    "You can tell me things about yourself and I'll remember them. "
    "Start every message with Jarvis. For example: Jarvis, remember that I work at Amazon."
)

HELP_MSG = (
    "I can remember facts about you and use them in our conversations. "
    "Try things like: remember that I love pizza, I want to learn guitar, "
    "or ask me what I know about you. Say forget to remove something. "
    "If you've linked your Google account, I can also manage your calendar."
)

FALLBACK_MSG = (
    "I didn't quite catch that. Try starting with a phrase like: "
    "Jarvis, tell me... or Jarvis remember that, or Jarvis, I think."
)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handles incoming Alexa requests.

    Args:
        event: The Alexa request event.
        context: The Lambda context object.

    Returns:
        An Alexa-formatted response dict.
    """
    try:
        request_type = event["request"]["type"]
        user_id = event["session"]["user"]["userId"]
        history = parse_history(event)

        if request_type == "SessionEndedRequest":
            logger.info("Session ended for user %s", user_id)
            return build_response("", end_session=True)

        elif request_type == "LaunchRequest":
            return build_response(LAUNCH_MSG, reprompt="I'm listening.")

        elif request_type == "IntentRequest":
            intent = event["request"]["intent"]["name"]

            if intent == "LogActivityIntent":
                utterance = event["request"]["intent"]["slots"]["freeText"]["value"]
                logger.info("User %s said: %s", user_id, utterance)
                extraction_service = build_extraction_service(event)
                response = extraction_service.process(user_id, utterance, history)
                session_attrs = update_history(history, utterance, response)
                return build_response(response, session_attributes=session_attrs, reprompt="Anything else?")

            elif intent in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
                return build_response("See you later.", end_session=True)

            elif intent == "AMAZON.HelpIntent":
                return build_response(HELP_MSG, reprompt="Go ahead, I'm listening.")

            elif intent == "AMAZON.FallbackIntent":
                return build_response(FALLBACK_MSG, reprompt="I'm still here.")

        return build_response("I didn't catch that.", reprompt="I'm still here.")

    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        return build_response("Something went wrong. Try again.", reprompt="I'm still here.")
