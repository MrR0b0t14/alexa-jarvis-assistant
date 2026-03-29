from typing import Any
from utils.response import build_response


def handle_log_intent(event: dict[str, Any]) -> dict[str, Any]:
    text: str = event['request']['intent']['slots']['freeText']['value']
    print(f"[LogIntent] User said: {text}")
    return build_response(f"Got it. You said: {text}")
