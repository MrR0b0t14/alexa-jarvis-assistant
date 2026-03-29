"""Orchestrates the memory extraction pipeline.

Flow: classify utterance → execute memory/calendar actions silently → return response.
"""

from typing import Optional
from models.memory import MemoryFact, CategoryRegistry
from models.calendar import CalendarEvent
from models.llm import AgentAction, AgentTaskDecision
from config.prompts import CLASSIFY_PROMPT, REWRITE_PROMPT
from config.logger import get_logger
from services.memory_service import MemoryService
from services.llm_service import LlmService
from services.calendar_service import CalendarService

logger = get_logger(__name__)


class ExtractionService:
    """Orchestrates the full extraction pipeline for a user utterance.

    Args:
        memory_service: DynamoDB memory operations.
        llm_service: Groq LLM API calls.
        calendar_service: Google Calendar operations (None if not linked).
    """

    def __init__(self, memory_service: MemoryService, llm_service: LlmService, calendar_service: Optional[CalendarService] = None) -> None:
        self.memory_service = memory_service
        self.llm_service = llm_service
        self.calendar_service = calendar_service
        self._action_handlers = {
            AgentAction.STORE: self._handle_store,
            AgentAction.DELETE: self._handle_delete,
            AgentAction.CALENDAR_ADD: self._handle_calendar_add,
            AgentAction.CALENDAR_QUERY: self._handle_calendar_query,
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
        has_calendar = self.calendar_service is not None

        logger.debug("Categories: %s | Facts: %d | Calendar: %s", list(registry.categories.keys()), len(facts), has_calendar)

        prompt = CLASSIFY_PROMPT.format(
            categories=registry.categories,
            memory_context=memory_context,
            utterance=utterance,
            has_calendar=has_calendar,
        )
        agent_response = self.llm_service.decide_task(prompt)

        logger.info("LLM decided: %d actions, response=%s", len(agent_response.actions), agent_response.response[:80])

        calendar_response: Optional[str] = None
        for action in agent_response.actions:
            handler = self._action_handlers[action.action]
            result = handler(user_id, utterance, action, registry)
            if result:
                calendar_response = result

        return calendar_response or agent_response.response

    def _handle_store(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> Optional[str]:
        """Stores or updates a memory fact."""
        logger.info("STORE action: category=%s", decision.category)

        if not registry.has(decision.category):
            logger.info("New category: %s — %s", decision.category, decision.description)
            registry.add(decision.category, decision.description)
            self.memory_service.save_categories(registry)

        existing = self.memory_service.get_fact(user_id, decision.category)
        current_value = existing.value if existing else "No existing data"

        prompt = REWRITE_PROMPT.format(
            category=decision.category,
            current_value=current_value,
            utterance=utterance,
        )
        new_value = self.llm_service.call_llm(prompt)

        fact = MemoryFact(
            user_id=user_id,
            category=decision.category,
            value=new_value,
            source_utterance=utterance,
        )
        self.memory_service.save_fact(fact)
        return None

    def _handle_delete(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> Optional[str]:
        """Deletes an entire memory category."""
        logger.info("DELETE action: category=%s", decision.category)
        self.memory_service.delete_fact(user_id, decision.category)
        return None

    def _handle_calendar_add(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> Optional[str]:
        """Adds an event to Google Calendar."""
        if not self.calendar_service:
            return "I'd love to add that to your calendar, but your Google account isn't linked yet. You can do that in the Alexa app."

        if not decision.event_summary or not decision.event_date:
            logger.warning("Missing event details: summary=%s date=%s", decision.event_summary, decision.event_date)
            return None

        logger.info("CALENDAR_ADD: %s on %s", decision.event_summary, decision.event_date)
        event = CalendarEvent(
            summary=decision.event_summary,
            date=decision.event_date,
            description=f"Created by Jarvis from: {utterance}",
            duration_hours=24,
        )
        self.calendar_service.create_event(event)
        return None

    def _handle_calendar_query(self, user_id: str, utterance: str, decision: AgentTaskDecision, registry: CategoryRegistry) -> Optional[str]:
        """Retrieves upcoming calendar events and formats a spoken response."""
        if not self.calendar_service:
            return "I can't check your calendar because your Google account isn't linked yet. You can link it in the Alexa app."

        logger.info("CALENDAR_QUERY")
        events = self.calendar_service.get_events()

        if not events:
            return "Your calendar is clear for the next week."

        lines = [f"{e.summary} on {e.date}" for e in events]
        return "Here's what's coming up: " + ". ".join(lines) + "."
