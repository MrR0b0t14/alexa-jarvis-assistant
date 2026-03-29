from dataclasses import dataclass
from enum import Enum

class AgentAction(Enum):
    STORE = "STORE"
    DELETE = "DELETE"
    CHAT = "CHAT"

@dataclass
class AgentTaskDecision:
    action: AgentAction
    category: str
    description: str

    @classmethod
    def from_agent(cls, response):
        return cls(
            action=AgentAction(response["action"]),
            category=response["category"],
            description=response["category_description"]
        )