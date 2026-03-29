import json
import pytest
from unittest.mock import MagicMock
from models.memory import MemoryFact, CategoryRegistry
from models.llm import AgentAction, AgentTaskDecision
from services.extraction_service import ExtractionService


@pytest.fixture
def memory_service():
    return MagicMock()


@pytest.fixture
def llm_service():
    return MagicMock()


@pytest.fixture
def extraction_service(memory_service, llm_service):
    return ExtractionService(memory_service, llm_service)


class TestExtractionServiceProcess:
    def test_dispatches_to_store_handler(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        llm_service.decide_task.return_value = AgentTaskDecision(
            action=AgentAction.STORE, category="employment", description="Jobs"
        )
        with pytest.raises(NotImplementedError):
            extraction_service.process("user_123", "I work at Amazon")

    def test_dispatches_to_delete_handler(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        llm_service.decide_task.return_value = AgentTaskDecision(
            action=AgentAction.DELETE, category="employment", description="Jobs"
        )
        with pytest.raises(NotImplementedError):
            extraction_service.process("user_123", "Forget my job info")

    def test_dispatches_to_chat_handler(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        llm_service.decide_task.return_value = AgentTaskDecision(
            action=AgentAction.CHAT, category="", description=""
        )
        with pytest.raises(NotImplementedError):
            extraction_service.process("user_123", "What's the weather?")

    def test_passes_categories_to_classify_prompt(self, extraction_service, memory_service, llm_service):
        registry = CategoryRegistry(user_id="user_123", categories={"employment": "Jobs"})
        memory_service.get_categories.return_value = registry
        llm_service.decide_task.return_value = AgentTaskDecision(
            action=AgentAction.CHAT, category="", description=""
        )
        with pytest.raises(NotImplementedError):
            extraction_service.process("user_123", "hello")

        prompt_arg = llm_service.decide_task.call_args[0][0]
        assert "employment" in prompt_arg
        assert "hello" in prompt_arg
