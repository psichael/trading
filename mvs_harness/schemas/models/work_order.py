from pydantic import BaseModel, Field
from typing import List

# Defines the structure for a WorkOrder, which is the input to the agent.
class WorkOrder(BaseModel):
    active_task: str
    task_content: str
    required_context_files: List[str] = Field(default_factory=list)

# Represents the state for the next work cycle, persisted to disk.
class ContextManifest(BaseModel):
    active_task: str
    task_content: str
