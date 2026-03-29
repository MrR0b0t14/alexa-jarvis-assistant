"""Data models for LLM interaction."""

from enum import Enum
from pydantic import BaseModel, Field


class AgentAction(Enum):
    """Possible memory side-effects the LLM can trigger.

    STORE: Save or update a memory fact.
    DELETE: Remove an entire memory category.
    """

    STORE = "STORE"
    DELETE = "DELETE"


class AgentTaskDecision(BaseModel):
    """A single memory operation extracted from user input.

    Attributes:
        action: Whether to store or delete.
        category: The memory category this relates to.
        description: Short description of the category (used when creating new ones).
    """

    model_config = {"populate_by_name": True}

    action: AgentAction
    category: str
    description: str = Field(alias="category_description")


class AgentResponse(BaseModel):
    """Full LLM decision: zero or more memory actions + a conversational response.

    The LLM always produces a response. Memory actions are optional side-effects
    that happen silently in the background.

    Attributes:
        actions: List of memory operations to execute (can be empty).
        response: Conversational response to speak back to the user.
    """

    actions: list[AgentTaskDecision] = Field(default_factory=list)
    response: str
