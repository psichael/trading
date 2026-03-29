from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- SPFv2 Planner Logical Proposal Models ---

class CreateComponent(BaseModel):
    temp_id: str
    title: str
    parent_component_id: str
    abstract: str

class CreateEpic(BaseModel):
    temp_id: str
    title: str
    insert_after_epic_id: Optional[str] = None
    component_ids: List[str]
    abstract: str

class CreateTaskInput(BaseModel):
    id: str
    source_task_id: str

class CreateTaskOutput(BaseModel):
    id: str
    type: str
    artifact_path: str

class CreateTask(BaseModel):
    temp_id: str
    title: str
    parent_epic_id: str
    insert_after_task_id: Optional[str] = None
    component_ids: List[str]
    implements_contract_id: str
    inputs: List[CreateTaskInput] = Field(default_factory=list)
    outputs: List[CreateTaskOutput] = Field(default_factory=list)
    content: str

class CreateContract(BaseModel):
    temp_id: str
    title: str
    parent_component_id: str
    version: str
    abstract: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class UpdateComponent(BaseModel):
    id: str
    title: Optional[str] = None
    parent_component_id: Optional[str] = None
    abstract: Optional[str] = None

class UpdateEpic(BaseModel):
    id: str
    title: Optional[str] = None
    status: Optional[str] = None
    component_ids: Optional[List[str]] = None
    abstract: Optional[str] = None

class UpdateTask(BaseModel):
    id: str
    title: Optional[str] = None
    status: Optional[str] = None
    component_ids: Optional[List[str]] = None
    implements_contract_id: Optional[str] = None
    insert_after_task_id: Optional[str] = None
    inputs: Optional[List[CreateTaskInput]] = None
    outputs: Optional[List[CreateTaskOutput]] = None
    content: Optional[str] = None

class UpdateContract(BaseModel):
    id: str
    title: Optional[str] = None
    status: Optional[str] = None
    abstract: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class DeleteItem(BaseModel):
    id: str

class CreateItems(BaseModel):
    components: List[CreateComponent] = Field(default_factory=list)
    epics: List[CreateEpic] = Field(default_factory=list)
    tasks: List[CreateTask] = Field(default_factory=list)
    contracts: List[CreateContract] = Field(default_factory=list)

class UpdateItems(BaseModel):
    components: List[UpdateComponent] = Field(default_factory=list)
    epics: List[UpdateEpic] = Field(default_factory=list)
    tasks: List[UpdateTask] = Field(default_factory=list)
    contracts: List[UpdateContract] = Field(default_factory=list)

class DeleteItems(BaseModel):
    components: List[DeleteItem] = Field(default_factory=list)
    epics: List[DeleteItem] = Field(default_factory=list)
    tasks: List[DeleteItem] = Field(default_factory=list)
    contracts: List[DeleteItem] = Field(default_factory=list)

class SpfProposal(BaseModel):
    create: Optional[CreateItems] = None
    update: Optional[UpdateItems] = None
    delete: Optional[DeleteItems] = None
