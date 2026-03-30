"""Data models for LLM interaction."""

from enum import Enum
from pydantic import BaseModel, Field


class AgentAction(Enum):
    """Possible side-effects the LLM can trigger.

    STORE: Save or update a memory fact.
    DELETE: Remove an entire memory category.
    CALENDAR_ADD: Add an event to Google Calendar.
    CALENDAR_QUERY: Retrieve upcoming calendar events.
    """

    STORE = "STORE"
    DELETE = "DELETE"
    CALENDAR_ADD = "CALENDAR_ADD"
    CALENDAR_QUERY = "CALENDAR_QUERY"


class AgentTaskDecision(BaseModel):
    """A single action extracted from user input.

    Attributes:
        action: The action type.
        category: The memory category (for STORE/DELETE).
        description: Short description of the category.
        event_summary: Event title (for CALENDAR_ADD).
        event_date: Event date in YYYY-MM-DD (for CALENDAR_ADD).
    """

    model_config = {"populate_by_name": True}

    action: AgentAction
    category: str = ""
    description: str = Field(default="", alias="category_description")
    event_summary: str = ""
    event_date: str = ""
    event_time: str = ""
    event_end_date: str = ""
    event_timezone: str = ""


class AgentResponse(BaseModel):
    """Full LLM decision: zero or more actions + a conversational response.

    Attributes:
        actions: List of actions to execute (can be empty).
        response: Conversational response to speak back to the user.
    """

    actions: list[AgentTaskDecision] = Field(default_factory=list)
    response: str
