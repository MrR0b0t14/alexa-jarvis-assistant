"""Data models for the memory system."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import json


@dataclass
class MemoryFact:
    """A single consolidated fact within a memory category.

    Each fact represents the current state of knowledge for a given category
    (e.g., "employment", "goal"). The value is a free-text paragraph that the
    LLM rewrites on every update — it is not append-only.

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
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dynamo(self) -> dict[str, str]:
        """Serializes this fact to a DynamoDB item.

        Returns:
            A dict ready to be passed to ``table.put_item()``.
        """
        return {
            "user_id": self.user_id,
            "category": self.category,
            "value": self.value,
            "source_utterance": self.source_utterance,
            "updated_at": self.updated_at,
        }

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


@dataclass
class CategoryRegistry:
    """Registry of known memory categories for a user.

    Stored as a single DynamoDB item with sort key "metadata#categories".
    The LLM picks from existing categories or proposes new ones, which are
    then added to this registry.

    Attributes:
        user_id: Alexa user identifier (partition key).
        categories: Map of category name to description.
        updated_at: ISO timestamp of the last update.
    """

    user_id: str
    categories: dict[str, str] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    METADATA_SK: str = "metadata#categories"

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
