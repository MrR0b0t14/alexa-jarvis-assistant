import json
import pytest
from models.memory import MemoryFact, CategoryRegistry
from models.llm import AgentAction, AgentTaskDecision, AgentResponse


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


class TestAgentAction:
    def test_store_action(self):
        assert AgentAction("STORE") == AgentAction.STORE

    def test_delete_action(self):
        assert AgentAction("DELETE") == AgentAction.DELETE

    def test_invalid_action(self):
        with pytest.raises(ValueError):
            AgentAction("INVALID")


class TestAgentTaskDecision:
    def test_model_validate(self):
        response = {
            "action": "STORE",
            "category": "employment",
            "category_description": "Jobs and roles",
        }
        decision = AgentTaskDecision.model_validate(response)
        assert decision.action == AgentAction.STORE
        assert decision.category == "employment"
        assert decision.description == "Jobs and roles"

    def test_model_validate_with_field_name(self):
        decision = AgentTaskDecision(
            action=AgentAction.DELETE, category="goal", description="Personal goals"
        )
        assert decision.action == AgentAction.DELETE

    def test_model_validate_invalid_action(self):
        response = {
            "action": "UNKNOWN",
            "category": "test",
            "category_description": "test",
        }
        with pytest.raises(ValueError):
            AgentTaskDecision.model_validate(response)


class TestAgentResponse:
    def test_with_actions(self):
        data = {
            "actions": [
                {"action": "STORE", "category": "employment", "category_description": "Jobs"},
                {"action": "STORE", "category": "goal", "category_description": "Goals"},
            ],
            "response": "Nice, got it!",
        }
        resp = AgentResponse.model_validate(data)
        assert len(resp.actions) == 2
        assert resp.actions[0].category == "employment"
        assert resp.actions[1].category == "goal"
        assert resp.response == "Nice, got it!"

    def test_empty_actions(self):
        data = {"actions": [], "response": "Just chatting!"}
        resp = AgentResponse.model_validate(data)
        assert resp.actions == []
        assert resp.response == "Just chatting!"

    def test_no_actions_field_defaults_to_empty(self):
        data = {"response": "Hello!"}
        resp = AgentResponse.model_validate(data)
        assert resp.actions == []

    def test_mixed_actions(self):
        data = {
            "actions": [
                {"action": "STORE", "category": "employment", "category_description": "Jobs"},
                {"action": "DELETE", "category": "health", "category_description": "Health"},
            ],
            "response": "Updated!",
        }
        resp = AgentResponse.model_validate(data)
        assert resp.actions[0].action == AgentAction.STORE
        assert resp.actions[1].action == AgentAction.DELETE
