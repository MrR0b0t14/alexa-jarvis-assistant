import boto3
from moto import mock_aws
from models.memory import MemoryFact, CategoryRegistry
from services.memory_service import MemoryService
import pytest


@pytest.fixture
def memory_service():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        dynamodb.create_table(
            TableName="user_memory",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "category", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield MemoryService(dynamodb.Table("user_memory"))


def _fact(
    user_id: str = "user_123", category: str = "employment", value: str = "Works at Amazon", utterance: str = "test"
) -> MemoryFact:
    return MemoryFact(user_id=user_id, category=category, value=value, source_utterance=utterance)


class TestMemoryService:
    def test_save_and_get_fact(self, memory_service):
        memory_service.save_fact(_fact())
        result = memory_service.get_fact("user_123", "employment")
        assert result is not None
        assert result.value == "Works at Amazon"

    def test_get_fact_not_found(self, memory_service):
        assert memory_service.get_fact("user_123", "nonexistent") is None

    def test_get_all_facts_excludes_metadata(self, memory_service):
        reg = CategoryRegistry(user_id="user_123", categories={"employment": "Jobs"})
        memory_service.save_categories(reg)
        memory_service.save_fact(_fact())
        memory_service.save_fact(_fact(category="goal", value="Run a marathon"))

        facts = memory_service.get_all_facts("user_123")
        categories = [f.category for f in facts]
        assert "employment" in categories
        assert "goal" in categories
        assert "metadata#categories" not in categories

    def test_delete_fact(self, memory_service):
        memory_service.save_fact(_fact())
        memory_service.delete_fact("user_123", "employment")
        assert memory_service.get_fact("user_123", "employment") is None

    def test_save_and_get_categories(self, memory_service):
        reg = CategoryRegistry(user_id="user_123")
        reg.add("employment", "Jobs and roles")
        reg.add("goal", "Personal goals")
        memory_service.save_categories(reg)

        result = memory_service.get_categories("user_123")
        assert result.has("employment")
        assert result.has("goal")

    def test_get_categories_empty(self, memory_service):
        result = memory_service.get_categories("user_123")
        assert result.categories == {}

    def test_overwrite_fact(self, memory_service):
        memory_service.save_fact(_fact(utterance="v1"))
        memory_service.save_fact(_fact(value="Works at Amazon as SDE3", utterance="v2"))
        result = memory_service.get_fact("user_123", "employment")
        assert result.value == "Works at Amazon as SDE3"
        assert result.source_utterance == "v2"
