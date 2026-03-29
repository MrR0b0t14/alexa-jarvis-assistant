import json
from unittest.mock import MagicMock
from services.llm_service import LlmService
from models.llm import AgentAction


def _mock_client(content: str) -> MagicMock:
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

    def test_decide_task_with_actions(self):
        response_json = json.dumps({
            "actions": [
                {"action": "STORE", "category": "employment", "category_description": "Jobs"},
            ],
            "response": "Got it!",
        })
        service = LlmService(_mock_client(response_json))
        result = service.decide_task("I work at Amazon")
        assert len(result.actions) == 1
        assert result.actions[0].action == AgentAction.STORE
        assert result.actions[0].category == "employment"
        assert result.response == "Got it!"

    def test_decide_task_no_actions(self):
        response_json = json.dumps({
            "actions": [],
            "response": "Just chatting!",
        })
        service = LlmService(_mock_client(response_json))
        result = service.decide_task("What's up?")
        assert result.actions == []
        assert result.response == "Just chatting!"

    def test_decide_task_multiple_actions(self):
        response_json = json.dumps({
            "actions": [
                {"action": "STORE", "category": "employment", "category_description": "Jobs"},
                {"action": "STORE", "category": "goal", "category_description": "Goals"},
            ],
            "response": "Busy life!",
        })
        service = LlmService(_mock_client(response_json))
        result = service.decide_task("I work at Amazon and want to run a marathon")
        assert len(result.actions) == 2

    def test_decide_task_strips_markdown_fences(self):
        response_json = '```json\n{"actions": [{"action": "STORE", "category": "goal", "category_description": "Goals"}], "response": "Nice!"}\n```'
        service = LlmService(_mock_client(response_json))
        result = service.decide_task("I want to run a marathon")
        assert len(result.actions) == 1
        assert result.response == "Nice!"
