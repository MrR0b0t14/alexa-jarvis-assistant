import pytest
from unittest.mock import MagicMock
from models.memory import MemoryFact, CategoryRegistry
from models.calendar import CalendarEventResult
from models.llm import AgentAction, AgentTaskDecision, AgentResponse
from services.extraction_service import ExtractionService


@pytest.fixture
def memory_service():
    return MagicMock()


@pytest.fixture
def llm_service():
    return MagicMock()


@pytest.fixture
def calendar_service():
    return MagicMock()


@pytest.fixture
def extraction_service(memory_service, llm_service):
    return ExtractionService(memory_service, llm_service)


@pytest.fixture
def extraction_service_with_calendar(memory_service, llm_service, calendar_service):
    return ExtractionService(memory_service, llm_service, calendar_service)


class TestExtractionServiceProcess:
    def test_returns_response_with_no_actions(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(actions=[], response="Hey there!")

        result = extraction_service.process("user_123", "hello")
        assert result == "Hey there!"

    def test_executes_store_action(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        memory_service.get_fact.return_value = None
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.STORE, category="employment", description="Jobs")],
            response="Cool!",
        )
        llm_service.call_llm.return_value = "Works at Amazon"

        result = extraction_service.process("user_123", "I work at Amazon")
        assert result == "Cool!"
        memory_service.save_fact.assert_called_once()
        memory_service.save_categories.assert_called_once()

    def test_executes_delete_action(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.DELETE, category="health", description="Health")],
            response="Forgotten!",
        )

        result = extraction_service.process("user_123", "Forget my health info")
        assert result == "Forgotten!"
        memory_service.delete_fact.assert_called_once_with("user_123", "health")

    def test_executes_multiple_actions(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        memory_service.get_fact.return_value = None
        llm_service.decide_task.return_value = AgentResponse(
            actions=[
                AgentTaskDecision(action=AgentAction.STORE, category="employment", description="Jobs"),
                AgentTaskDecision(action=AgentAction.STORE, category="goal", description="Goals"),
            ],
            response="Busy life!",
        )
        llm_service.call_llm.return_value = "Some fact"

        result = extraction_service.process("user_123", "I work at Amazon and want to run a marathon")
        assert result == "Busy life!"
        assert memory_service.save_fact.call_count == 2

    def test_store_reuses_existing_category(self, extraction_service, memory_service, llm_service):
        registry = CategoryRegistry(user_id="user_123", categories={"employment": "Jobs"})
        memory_service.get_categories.return_value = registry
        memory_service.get_all_facts.return_value = []
        memory_service.get_fact.return_value = MemoryFact("user_123", "employment", "Works at Google", "old")
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.STORE, category="employment", description="Jobs")],
            response="Updated!",
        )
        llm_service.call_llm.return_value = "Works at Amazon, previously Google"

        extraction_service.process("user_123", "I now work at Amazon")
        memory_service.save_categories.assert_not_called()

    def test_passes_categories_to_prompt(self, extraction_service, memory_service, llm_service):
        registry = CategoryRegistry(user_id="user_123", categories={"employment": "Jobs"})
        memory_service.get_categories.return_value = registry
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(actions=[], response="Hi!")

        extraction_service.process("user_123", "hello")
        prompt_arg = llm_service.decide_task.call_args[0][0]
        assert "employment" in prompt_arg
        assert "hello" in prompt_arg


class TestCalendarActions:
    def test_calendar_add_with_service(
        self, extraction_service_with_calendar, memory_service, llm_service, calendar_service
    ):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[
                AgentTaskDecision(
                    action=AgentAction.CALENDAR_ADD,
                    event_summary="Trip to China",
                    event_date="2026-10-15",
                )
            ],
            response="Added your China trip to the calendar!",
        )

        result = extraction_service_with_calendar.process(
            "user_123", "Add my China trip to the calendar on October 15th"
        )
        assert result == "Added your China trip to the calendar!"
        calendar_service.create_event.assert_called_once()

    def test_calendar_add_without_service(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[
                AgentTaskDecision(
                    action=AgentAction.CALENDAR_ADD,
                    event_summary="Trip",
                    event_date="2026-10-15",
                )
            ],
            response="Sure!",
        )

        result = extraction_service.process("user_123", "Add trip to calendar")
        assert "isn't linked" in result

    def test_calendar_add_missing_details(self, extraction_service_with_calendar, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.CALENDAR_ADD)],
            response="What event?",
        )

        result = extraction_service_with_calendar.process("user_123", "add to calendar")
        assert result == "What event?"

    def test_calendar_add_invalid_date(
        self, extraction_service_with_calendar, memory_service, llm_service, calendar_service
    ):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        calendar_service.create_event.side_effect = ValueError("Invalid date")
        llm_service.decide_task.return_value = AgentResponse(
            actions=[
                AgentTaskDecision(
                    action=AgentAction.CALENDAR_ADD,
                    event_summary="Dinner",
                    event_date="tomorrow",
                )
            ],
            response="Added!",
        )

        result = extraction_service_with_calendar.process("user_123", "add dinner tomorrow")
        assert "didn't look right" in result

    def test_calendar_query_with_events(
        self, extraction_service_with_calendar, memory_service, llm_service, calendar_service
    ):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        calendar_service.get_events.return_value = [
            CalendarEventResult(summary="Team standup", date="2026-03-30"),
            CalendarEventResult(summary="Dentist", date="2026-04-01"),
        ]
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.CALENDAR_QUERY)],
            response="Let me check...",
        )

        result = extraction_service_with_calendar.process("user_123", "What's on my calendar?")
        assert "Team standup" in result
        assert "Dentist" in result

    def test_calendar_query_empty(
        self, extraction_service_with_calendar, memory_service, llm_service, calendar_service
    ):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        calendar_service.get_events.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.CALENDAR_QUERY)],
            response="Let me check...",
        )

        result = extraction_service_with_calendar.process("user_123", "What's on my calendar?")
        assert "clear" in result

    def test_calendar_query_without_service(self, extraction_service, memory_service, llm_service):
        memory_service.get_categories.return_value = CategoryRegistry(user_id="user_123")
        memory_service.get_all_facts.return_value = []
        llm_service.decide_task.return_value = AgentResponse(
            actions=[AgentTaskDecision(action=AgentAction.CALENDAR_QUERY)],
            response="Let me check...",
        )

        result = extraction_service.process("user_123", "What's on my calendar?")
        assert "isn't linked" in result
