"""Groq LLM API integration."""

import json
from typing import Any
from models.llm import AgentResponse
from config.logger import get_logger

MODEL = "llama-3.3-70b-versatile"
logger = get_logger(__name__)


class LlmService:
    """Handles all LLM API calls via the Groq client.

    Uses dependency injection for the Groq client, making it easy to
    mock in tests.

    Args:
        client: A Groq client instance.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def call_llm(self, prompt: str) -> str:
        """Sends a prompt to the LLM and returns the raw text response.

        Args:
            prompt: The full prompt string to send.

        Returns:
            The LLM's response text, stripped of whitespace.
        """
        logger.debug("LLM prompt: %s", prompt[:200])
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        content: str = response.choices[0].message.content.strip()
        logger.debug("LLM response: %s", content[:200])
        return content

    def decide_task(self, prompt: str) -> AgentResponse:
        """Sends a classification prompt and returns a structured response.

        Parses the LLM's JSON into an ``AgentResponse`` containing zero or more
        memory actions and a conversational response. Handles markdown code
        fences that some models wrap around JSON.

        Args:
            prompt: The classification prompt with categories and utterance.

        Returns:
            An ``AgentResponse`` with actions and a response string.
        """
        raw = self.call_llm(prompt)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return AgentResponse.model_validate(json.loads(raw))
