"""Data models for the memory system."""

from datetime import datetime, timezone
from typing import Any, ClassVar
import json

from pydantic import BaseModel, Field


class MemoryFact(BaseModel):
    """A single consolidated fact within a memory category.

    Attributes:
        user_id: Alexa user identifier (partition key).
        category: The memory category this fact belongs to (sort key).
        value: The consolidated fact text, rewritten by the LLM.
        source_utterance: The last user input that triggered a rewrite.
        updated_at: ISO timestamp of the last update.
    """

    user_id: str
    category: str
    value: str
    source_utterance: str
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dynamo(self) -> dict[str, str]:
        """Serializes this fact to a DynamoDB item.

        Returns:
            A dict ready to be passed to ``table.put_item()``.
        """
        return self.model_dump()

    @classmethod
    def from_dynamo(cls, item: dict[str, Any]) -> "MemoryFact":
        """Deserializes a DynamoDB item into a MemoryFact.

        Args:
            item: A DynamoDB item dict from ``get_item`` or ``query``.

        Returns:
            A ``MemoryFact`` instance.
        """
        return cls(
            user_id=item["user_id"],
            category=item["category"],
            value=item["value"],
            source_utterance=item.get("source_utterance", ""),
            updated_at=item.get("updated_at", ""),
        )


class CategoryRegistry(BaseModel):
    """Registry of known memory categories for a user.

    Stored as a single DynamoDB item with sort key "metadata#categories".

    Attributes:
        user_id: Alexa user identifier (partition key).
        categories: Map of category name to description.
        updated_at: ISO timestamp of the last update.
    """

    user_id: str
    categories: dict[str, str] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    METADATA_SK: ClassVar[str] = "metadata#categories"

    def to_dynamo(self) -> dict[str, str]:
        """Serializes this registry to a DynamoDB item.

        Returns:
            A dict ready to be passed to ``table.put_item()``.
        """
        return {
            "user_id": self.user_id,
            "category": self.METADATA_SK,
            "value": json.dumps(self.categories),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dynamo(cls, item: dict[str, Any]) -> "CategoryRegistry":
        """Deserializes a DynamoDB item into a CategoryRegistry.

        Args:
            item: A DynamoDB item dict from ``get_item``.

        Returns:
            A ``CategoryRegistry`` instance.
        """
        return cls(
            user_id=item["user_id"],
            categories=json.loads(item["value"]),
            updated_at=item.get("updated_at", ""),
        )

    def add(self, name: str, description: str) -> None:
        """Adds a new category to the registry.

        Args:
            name: The category name (e.g., "employment").
            description: A short description of what this category covers.
        """
        self.categories[name] = description
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def has(self, name: str) -> bool:
        """Checks if a category exists in the registry.

        Args:
            name: The category name to look up.

        Returns:
            True if the category exists, False otherwise.
        """
        return name in self.categories


class HistoryEvent(BaseModel):
    """A single interaction between the user and the agent.

    Attributes:
        user_request: What the user said.
        agent_reply: What Jarvis responded.
    """

    user_request: str
    agent_reply: str


class History(BaseModel):
    """Conversation history within an Alexa session.

    Attributes:
        exchanges: List of user/agent interactions, capped at 20.
    """

    exchanges: list[HistoryEvent] = Field(default_factory=list)

    def add(self, event: HistoryEvent) -> None:
        """Adds a new exchange and caps at 20 entries (Alexa 24KB session limit).

        Args:
            event: The new history event.
        """
        self.exchanges.append(event)
        self.exchanges = self.exchanges[-20:]
