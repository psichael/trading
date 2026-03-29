from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from .common import ContextFile, LogEntry

# NEW: Represents the contextual manifesto for the current epic.
class EpicContext(BaseModel):
    manifesto_path: str
    manifesto_content: str

# Represents the overall state of the project at the start of a cycle.
class ProjectState(BaseModel):
    active_task: Optional[str]
    active_task_content: Optional[str]
    recent_events: List[LogEntry]
    file_tree: str
    context_files: List[ContextFile] = Field(default_factory=list)
    plan_tree: Optional[str] = None

# A structured representation of the governing protocol for the Orchestrator.
class GoverningProtocol(BaseModel):
    protocol_name: str
    source_file: str
    content: str

# NEW: Represents the schema for an SDF-based plan task document.
class SdfPlanTask(BaseModel):
    id: str
    type: Literal["task"] = "task"
    status: str
    dependencies: Optional[List[str]] = None
    content: str
