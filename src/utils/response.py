from typing import Any


def build_response(text: str, end_session: bool = False) -> dict[str, Any]:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": end_session
        }
    }
