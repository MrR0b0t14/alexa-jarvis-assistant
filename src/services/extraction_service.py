"""Orchestrates the memory extraction pipeline.

Flow: classify utterance → execute memory actions silently → return response.
"""

from models.memory import MemoryFact, CategoryRegistry
from models.llm import AgentAction, AgentTaskDecision
from config.prompts import CLASSIFY_PROMPT, REWRITE_PROMPT
from config.logger import get_logger
from services.memory_service import MemoryService
from services.llm_service import LlmService

logger = get_logger(__name__)


class ExtractionService:
    """Orchestrates the full extraction pipeline for a user utterance.

    1. Reads existing categories and facts from DynamoDB.
    2. Asks the LLM to classify the utterance and respond.
    3. Executes any memory actions (STORE/DELETE) silently.
    4. Returns the conversational response.

    Args:
        memory_service: DynamoDB memory operations.
        llm_service: Groq LLM API calls.
    """

    def __init__(self, memory_service: MemoryService, llm_service: LlmService) -> None:
        self.memory_service = memory_service
        self.llm_service = llm_service
        self._action_handlers = {
            AgentAction.STORE: self._handle_store,
            AgentAction.DELETE: self._handle_delete,
        }

    def process(self, user_id: str, utterance: str) -> str:
        """Processes a user utterance through the full extraction pipeline.

        Args:
            user_id: The Alexa user identifier.
            utterance: The raw text the user spoke.

        Returns:
            The conversational response to speak back to the user.
        """
        logger.info("Processing utterance for user=%s: %s", user_id, utterance)

        registry = self.memory_service.get_categories(user_id)
        facts = self.memory_service.get_all_facts(user_id)
        memory_context = "\n".join(f"- {f.category}: {f.value}" for f in facts) or "No information stored yet."

        logger.debug("Categories: %s | Facts: %d", list(registry.categories.keys()), len(facts))

        prompt = CLASSIFY_PROMPT.format(
            categories=registry.categories,
            memory_context=memory_context,
            utterance=utterance,
        )
        agent_response = self.llm_service.decide_task(prompt)

        logger.info("LLM decided: %d actions, response=%s", len(agent_response.actions), agent_response.response[:80])

        for action in agent_response.actions:
            handler = self._action_handlers[action.action]
            handler(user_id, utterance, action, registry)

        return agent_response.response

    def _handle_store(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> None:
        """Stores or updates a memory fact.

        If the category is new, adds it to the registry first. Then reads
        the existing fact (if any), asks the LLM to rewrite it with the
        new information, and saves the result.

        Args:
            user_id: The Alexa user identifier.
            utterance: The raw text the user spoke.
            decision: The LLM's decision for this action.
            registry: The user's current category registry.
        """
        logger.info("STORE action: category=%s", decision.category)

        if not registry.has(decision.category):
            logger.info("New category: %s — %s", decision.category, decision.description)
            registry.add(decision.category, decision.description)
            self.memory_service.save_categories(registry)

        existing = self.memory_service.get_fact(user_id, decision.category)
        current_value = existing.value if existing else "No existing data"

        logger.debug("Existing value: %s", current_value[:100] if existing else "None")

        prompt = REWRITE_PROMPT.format(
            category=decision.category,
            current_value=current_value,
            utterance=utterance,
        )
        new_value = self.llm_service.call_llm(prompt)

        logger.debug("Rewritten value: %s", new_value[:100])

        fact = MemoryFact(
            user_id=user_id,
            category=decision.category,
            value=new_value,
            source_utterance=utterance,
        )
        self.memory_service.save_fact(fact)

    def _handle_delete(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> None:
        """Deletes an entire memory category.

        Args:
            user_id: The Alexa user identifier.
            utterance: The raw text the user spoke.
            decision: The LLM's decision for this action.
            registry: The user's current category registry.
        """
        logger.info("DELETE action: category=%s", decision.category)
        self.memory_service.delete_fact(user_id, decision.category)
