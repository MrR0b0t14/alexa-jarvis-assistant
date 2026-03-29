from models.memory import MemoryFact
from models.llm import AgentAction, AgentTaskDecision
from config.prompts import CLASSIFY_PROMPT, REWRITE_PROMPT, CHAT_PROMPT


class ExtractionService:
    def __init__(self, memory_service, llm_service):
        self.memory_service = memory_service
        self.llm_service = llm_service
        self._handlers = {
            AgentAction.STORE: self._handle_store,
            AgentAction.DELETE: self._handle_delete,
            AgentAction.CHAT: self._handle_chat,
        }

    def process(self, user_id: str, utterance: str) -> dict:
        registry = self.memory_service.get_categories(user_id)
        prompt = CLASSIFY_PROMPT.format(categories=registry.categories, utterance=utterance)
        decision = self.llm_service.decide_task(prompt)
        handler = self._handlers[decision.action]
        return handler(user_id, utterance, decision, registry)

    def _handle_store(self, user_id, utterance, decision, registry):
        # TODO: implement store logic
        raise NotImplementedError()

    def _handle_delete(self, user_id, utterance, decision, registry):
        # TODO: implement delete logic
        raise NotImplementedError()

    def _handle_chat(self, user_id, utterance, decision, registry):
        # TODO: implement chat logic
        raise NotImplementedError()
