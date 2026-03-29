from enum import Enum
from pydantic import BaseModel, Field

class AgentAction(Enum):
    STORE = "STORE"
    DELETE = "DELETE"
    CHAT = "CHAT"

class AgentTaskDecision(BaseModel):
    model_config = {"populate_by_name": True}    
    
    action: AgentAction
    category: str
    description: str = Field(alias="category_description")