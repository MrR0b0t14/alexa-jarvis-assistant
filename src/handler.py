"""Lambda entry point for the Alexa Jarvis Assistant."""

import os
import json as json_lib
import urllib.request
from typing import Any, Optional
import boto3
from groq import Groq
from services.memory_service import MemoryService
from services.llm_service import LlmService
from services.extraction_service import ExtractionService
from services.calendar_service import CalendarService
from utils.response import build_response
from config.logger import get_logger

logger = get_logger(__name__)

_memory_service: Optional[MemoryService] = None
_llm_service: Optional[LlmService] = None

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


def _get_base_services() -> tuple[MemoryService, LlmService]:
    """Lazily initializes and returns the base services.

    Returns:
        A tuple of (MemoryService, LlmService).
    """
    global _memory_service, _llm_service
    if _memory_service is None:
        table = boto3.resource("dynamodb", region_name="eu-west-1").Table("user_memory")
        _memory_service = MemoryService(table)
    if _llm_service is None:
        _llm_service = LlmService(Groq(api_key=os.environ["GROQ_API_KEY"]))
    return _memory_service, _llm_service


def _get_device_timezone(event: dict[str, Any]) -> str:
    """Gets the device timezone from the Alexa Settings API.

    Args:
        event: The Alexa request event.

    Returns:
        IANA timezone string (e.g., "Europe/Rome"). Defaults to "UTC".
    """
    try:
        system = event.get("context", {}).get("System", {})
        api_endpoint = system.get("apiEndpoint", "")
        api_token = system.get("apiAccessToken", "")
        device_id = system.get("device", {}).get("deviceId", "")

        if not all([api_endpoint, api_token, device_id]):
            return "UTC"

        url = f"{api_endpoint}/v2/devices/{device_id}/settings/System.timeZone"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_token}"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            tz = json_lib.loads(resp.read().decode())
            logger.info("Device timezone: %s", tz)
            return str(tz)
    except Exception as e:
        logger.warning("Failed to get timezone: %s", str(e))
        return "UTC"


def _build_extraction_service(event: dict[str, Any]) -> ExtractionService:
    """Builds an ExtractionService with optional calendar support.

    Calendar is available only if the user has linked their Google account.

    Args:
        event: The Alexa request event.

    Returns:
        An ``ExtractionService`` instance.
    """
    memory_service, llm_service = _get_base_services()

    access_token = event.get("context", {}).get("System", {}).get("user", {}).get("accessToken")
    calendar_service = None

    if not access_token:
        logger.info("No Google account linked — calendar disabled")
    else:
        calendar_service = CalendarService(access_token, _get_device_timezone(event))

    return ExtractionService(memory_service, llm_service, calendar_service)


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
                extraction_service = _build_extraction_service(event)
                response = extraction_service.process(user_id, utterance)
                return build_response(response, reprompt="Anything else?")

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
