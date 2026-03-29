from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from .spf import SpfProposal

# Defines a single file operation command.
class Command(BaseModel):
    command: Literal[
        "create_file", "update_file", "delete_file", "move_file",
        "create_directory", "move_directory", "delete_directory"
    ]
    path: str
    content: Optional[str] = None
    new_path: Optional[str] = None

# NEW: Formal structure for a plan update request from an agent.
class PlanUpdateRequest(BaseModel):
    problem_statement: str
    suggested_fix: str

# Formal structure for a context file request from an agent.
class ContextRequest(BaseModel):
    response_type: Literal["context_request"]
    requested_files: List[str]

# This is the root model for the agent's proposal JSON.
class Proposal(BaseModel):
    plan_analysis: str
    summary: str
    event_type: str
    commands: List[Command] = Field(
        default_factory=list,
        description="For Implementer Agents: A list of direct filesystem commands. Mutually exclusive with 'spf_plan_update'."
    )
    spf_plan_update: Optional[SpfProposal] = Field(
        default=None,
        description="For Planner Agents: A logical plan update to be compiled. Mutually exclusive with 'commands'."
    )
    completed_task_path: Optional[str] = None
    plan_update_request: Optional[PlanUpdateRequest] = None # For triage workflow
    context_request: Optional[ContextRequest] = None # For requesting missing files