from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import json


@dataclass
class MemoryFact:
    user_id: str
    category: str
    value: str
    source_utterance: str
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dynamo(self):
        return {
            "user_id": self.user_id,
            "category": self.category,
            "value": self.value,
            "source_utterance": self.source_utterance,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dynamo(cls, item):
        return cls(
            user_id=item["user_id"],
            category=item["category"],
            value=item["value"],
            source_utterance=item.get("source_utterance", ""),
            updated_at=item.get("updated_at", ""),
        )


@dataclass
class CategoryRegistry:
    user_id: str
    categories: dict = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    METADATA_SK = "metadata#categories"

    def to_dynamo(self):
        return {
            "user_id": self.user_id,
            "category": self.METADATA_SK,
            "value": json.dumps(self.categories),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dynamo(cls, item):
        return cls(
            user_id=item["user_id"],
            categories=json.loads(item["value"]),
            updated_at=item.get("updated_at", ""),
        )

    def add(self, name, description):
        self.categories[name] = description
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def has(self, name):
        return name in self.categories
