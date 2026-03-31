"""Alexa response builder."""

from typing import Any, Optional


def build_response(
    text: str,
    end_session: bool = False,
    reprompt: Optional[str] = None,
    session_attributes: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Builds an Alexa-formatted response.

    Args:
        text: The text Alexa will speak.
        end_session: Whether to close the session after speaking.
        reprompt: Text to speak if the user doesn't respond.

    Returns:
        An Alexa response dict.
    """
    response: dict[str, Any] = {
        "outputSpeech": {"type": "PlainText", "text": text},
        "shouldEndSession": end_session,
    }
    if reprompt:
        response["reprompt"] = {"outputSpeech": {"type": "PlainText", "text": reprompt}}
    return {"version": "1.0", "response": response}
