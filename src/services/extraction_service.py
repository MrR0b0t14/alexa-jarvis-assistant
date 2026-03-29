from typing import Callable
from models.memory import MemoryFact, CategoryRegistry
from models.llm import AgentAction, AgentTaskDecision
from config.prompts import CLASSIFY_PROMPT, REWRITE_PROMPT, CHAT_PROMPT
from services.memory_service import MemoryService
from services.llm_service import LlmService


class ExtractionService:
    def __init__(self, memory_service: MemoryService, llm_service: LlmService) -> None:
        self.memory_service = memory_service
        self.llm_service = llm_service
        self._handlers: dict[AgentAction, Callable[..., dict[str, str]]] = {
            AgentAction.STORE: self._handle_store,
            AgentAction.DELETE: self._handle_delete,
            AgentAction.CHAT: self._handle_chat,
        }

    def process(self, user_id: str, utterance: str) -> dict[str, str]:
        registry = self.memory_service.get_categories(user_id)
        prompt = CLASSIFY_PROMPT.format(categories=registry.categories, utterance=utterance)
        decision = self.llm_service.decide_task(prompt)
        handler = self._handlers[decision.action]
        return handler(user_id, utterance, decision, registry)

    def _handle_store(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> dict[str, str]:
        # TODO: implement store logic
        raise NotImplementedError()

    def _handle_delete(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> dict[str, str]:
        # TODO: implement delete logic
        raise NotImplementedError()

    def _handle_chat(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> dict[str, str]:
        # TODO: implement chat logic
        raise NotImplementedError()
