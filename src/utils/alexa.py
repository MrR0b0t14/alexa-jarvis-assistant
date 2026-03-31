"""Alexa request helpers — timezone detection and service wiring."""

import os
import json as json_lib
import urllib.request
from typing import Any, Optional
import boto3
from groq import Groq
from models.memory import History, HistoryEvent
from services.memory_service import MemoryService
from services.llm_service import LlmService
from services.extraction_service import ExtractionService
from services.calendar_service import CalendarService
from config.logger import get_logger

logger = get_logger(__name__)

_memory_service: Optional[MemoryService] = None
_llm_service: Optional[LlmService] = None


def get_base_services() -> tuple[MemoryService, LlmService]:
    """Lazily initializes and returns the base services (singleton).

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


def get_device_timezone(event: dict[str, Any]) -> str:
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


def build_extraction_service(event: dict[str, Any]) -> ExtractionService:
    """Builds an ExtractionService with optional calendar support.

    Calendar is available only if the user has linked their Google account.

    Args:
        event: The Alexa request event.

    Returns:
        An ``ExtractionService`` instance.
    """
    memory_service, llm_service = get_base_services()

    access_token = event.get("context", {}).get("System", {}).get("user", {}).get("accessToken")
    calendar_service = None

    if not access_token:
        logger.info("No Google account linked — calendar disabled")
    else:
        calendar_service = CalendarService(access_token, get_device_timezone(event))

    return ExtractionService(memory_service, llm_service, calendar_service)


def parse_history(event: dict[str, Any]) -> History:
    """Parses conversation history from Alexa session attributes.

    Args:
        event: The Alexa request event.

    Returns:
        A ``History`` instance with previous exchanges.
    """
    entries = event["session"].get("attributes", {}).get("history", [])
    return History(exchanges=entries)


def update_history(history: History, utterance: str, response: str) -> dict[str, Any]:
    """Appends a new exchange to the history and returns session attributes.

    Args:
        history: The current conversation history.
        utterance: What the user said.
        response: What Jarvis replied.

    Returns:
        A dict suitable for Alexa ``sessionAttributes``.
    """
    history.add(HistoryEvent(user_request=utterance, agent_reply=response))
    return {"history": history.model_dump()["exchanges"]}
