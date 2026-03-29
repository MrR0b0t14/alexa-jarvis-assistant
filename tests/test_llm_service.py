import json
from unittest.mock import MagicMock
from services.llm_service import LlmService
from models.llm import AgentAction


def _mock_client(content):
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    return client


class TestLlmService:
    def test_call_llm(self):
        client = _mock_client("Hello there")
        service = LlmService(client)
        result = service.call_llm("test prompt")
        assert result == "Hello there"
        client.chat.completions.create.assert_called_once()

    def test_call_llm_strips_whitespace(self):
        client = _mock_client("  some response  \n")
        service = LlmService(client)
        assert service.call_llm("test") == "some response"

    def test_decide_task_store(self):
        response_json = json.dumps({
            "action": "STORE",
            "category": "employment",
            "category_description": "Jobs and roles",
        })
        service = LlmService(_mock_client(response_json))
        decision = service.decide_task("I work at Amazon")
        assert decision.action == AgentAction.STORE
        assert decision.category == "employment"
        assert decision.description == "Jobs and roles"

    def test_decide_task_chat(self):
        response_json = json.dumps({
            "action": "CHAT",
            "category": "",
            "category_description": "",
        })
        service = LlmService(_mock_client(response_json))
        decision = service.decide_task("What's the weather?")
        assert decision.action == AgentAction.CHAT

    def test_decide_task_delete(self):
        response_json = json.dumps({
            "action": "DELETE",
            "category": "employment",
            "category_description": "Jobs and roles",
        })
        service = LlmService(_mock_client(response_json))
        decision = service.decide_task("Forget my job info")
        assert decision.action == AgentAction.DELETE

    def test_decide_task_strips_markdown_fences(self):
        response_json = '```json\n{"action": "STORE", "category": "goal", "category_description": "Personal goals"}\n```'
        service = LlmService(_mock_client(response_json))
        decision = service.decide_task("I want to run a marathon")
        assert decision.action == AgentAction.STORE
        assert decision.category == "goal"
