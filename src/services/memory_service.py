"""DynamoDB operations for the memory system."""

from typing import Any, Optional
from models.memory import MemoryFact, CategoryRegistry

TABLE_NAME = "user_memory"


class MemoryService:
    """Handles all DynamoDB read/write operations for memory facts and categories.

    Uses dependency injection for the DynamoDB table, making it easy to
    mock in tests.

    Args:
        table: A boto3 DynamoDB Table resource.
    """

    def __init__(self, table: Any) -> None:
        self.table = table

    def get_categories(self, user_id: str) -> CategoryRegistry:
        """Retrieves the category registry for a user.

        Args:
            user_id: The Alexa user identifier.

        Returns:
            The user's ``CategoryRegistry``, or an empty one if none exists.
        """
        resp = self.table.get_item(Key={"user_id": user_id, "category": CategoryRegistry.METADATA_SK})
        item = resp.get("Item")
        if not item:
            return CategoryRegistry(user_id=user_id)
        return CategoryRegistry.from_dynamo(item)

    def save_categories(self, registry: CategoryRegistry) -> None:
        """Persists a category registry to DynamoDB.

        Args:
            registry: The ``CategoryRegistry`` to save.
        """
        self.table.put_item(Item=registry.to_dynamo())

    def get_fact(self, user_id: str, category: str) -> Optional[MemoryFact]:
        """Retrieves a single memory fact by category.

        Args:
            user_id: The Alexa user identifier.
            category: The memory category to look up.

        Returns:
            The ``MemoryFact`` if found, or ``None``.
        """
        resp = self.table.get_item(Key={"user_id": user_id, "category": category})
        item = resp.get("Item")
        if not item:
            return None
        return MemoryFact.from_dynamo(item)

    def get_all_facts(self, user_id: str) -> list[MemoryFact]:
        """Retrieves all memory facts for a user, excluding metadata.

        Args:
            user_id: The Alexa user identifier.

        Returns:
            A list of ``MemoryFact`` instances.
        """
        resp = self.table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )
        return [
            MemoryFact.from_dynamo(i) for i in resp.get("Items", []) if i["category"] != CategoryRegistry.METADATA_SK
        ]

    def save_fact(self, fact: MemoryFact) -> None:
        """Persists a memory fact to DynamoDB. Overwrites if it already exists.

        Args:
            fact: The ``MemoryFact`` to save.
        """
        self.table.put_item(Item=fact.to_dynamo())

    def delete_fact(self, user_id: str, category: str) -> None:
        """Deletes a memory fact by category.

        Args:
            user_id: The Alexa user identifier.
            category: The memory category to delete.
        """
        self.table.delete_item(Key={"user_id": user_id, "category": category})
