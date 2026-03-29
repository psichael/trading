from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .common import ContextFile, LogEntry
from .work_order import WorkOrder
from .project_state import EpicContext, GoverningProtocol, ProjectState

# REFACTORED: The complete, hierarchical prompt provided to the agent.
class AgentPrompt(BaseModel):
    core_context: Dict[str, Any] = Field(default_factory=dict)
    epic_context: Optional[EpicContext] = None
    work_order: WorkOrder
    context_files: List[ContextFile]
    recent_events: List[LogEntry]
    file_tree: str
    operational_protocol: str
    agent_knowledge_base: Optional[str] = None

# The root object for the orchestrator prompt, enforcing hierarchy.
class OrchestratorPrompt(BaseModel):
    governing_protocol: GoverningProtocol
    project_state: ProjectState
    injected_context_files: Optional[List[ContextFile]] = None
