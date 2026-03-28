import json
import pytest
from models.memory import MemoryFact, CategoryRegistry


class TestMemoryFact:
    def test_to_dynamo(self):
        fact = MemoryFact(
            user_id="user_123",
            category="employment",
            value="Works at Amazon as SDE2",
            source_utterance="I work at Amazon as SDE2",
        )
        item = fact.to_dynamo()
        assert item["user_id"] == "user_123"
        assert item["category"] == "employment"
        assert item["value"] == "Works at Amazon as SDE2"
        assert item["source_utterance"] == "I work at Amazon as SDE2"
        assert "updated_at" in item

    def test_from_dynamo(self):
        item = {
            "user_id": "user_123",
            "category": "employment",
            "value": "Works at Amazon",
            "source_utterance": "I work at Amazon",
            "updated_at": "2026-03-28T23:00:00+00:00",
        }
        fact = MemoryFact.from_dynamo(item)
        assert fact.user_id == "user_123"
        assert fact.category == "employment"
        assert fact.value == "Works at Amazon"

    def test_from_dynamo_missing_optional_fields(self):
        item = {
            "user_id": "user_123",
            "category": "goal",
            "value": "Run a marathon",
        }
        fact = MemoryFact.from_dynamo(item)
        assert fact.source_utterance == ""
        assert fact.updated_at == ""


class TestCategoryRegistry:
    def test_empty_registry(self):
        reg = CategoryRegistry(user_id="user_123")
        assert reg.categories == {}
        assert not reg.has("employment")

    def test_add_category(self):
        reg = CategoryRegistry(user_id="user_123")
        reg.add("employment", "Jobs and roles")
        assert reg.has("employment")
        assert reg.categories["employment"] == "Jobs and roles"

    def test_to_dynamo(self):
        reg = CategoryRegistry(user_id="user_123", categories={"goal": "Personal goals"})
        item = reg.to_dynamo()
        assert item["user_id"] == "user_123"
        assert item["category"] == "metadata#categories"
        assert json.loads(item["value"]) == {"goal": "Personal goals"}

    def test_from_dynamo(self):
        item = {
            "user_id": "user_123",
            "category": "metadata#categories",
            "value": json.dumps({"employment": "Jobs", "goal": "Goals"}),
            "updated_at": "2026-03-28T23:00:00+00:00",
        }
        reg = CategoryRegistry.from_dynamo(item)
        assert reg.has("employment")
        assert reg.has("goal")
        assert len(reg.categories) == 2

    def test_roundtrip(self):
        reg = CategoryRegistry(user_id="user_123")
        reg.add("health", "Health info")
        reg.add("skill", "Skills and learning")
        item = reg.to_dynamo()
        restored = CategoryRegistry.from_dynamo(item)
        assert restored.categories == reg.categories
