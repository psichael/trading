from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

# These models represent the final, on-disk state of the plan artifacts
# or their in-memory representation in the plan graph.

class SpfComponentManifest(BaseModel):
    id: str
    title: str
    parent_component_id: str
    abstract: str
    type: Literal["spf-component-manifest"] = "spf-component-manifest"

class SpfContractDefinition(BaseModel):
    id: str
    title: str
    parent_component_id: str
    version: str
    abstract: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    type: Literal["spf-contract-definition"] = "spf-contract-definition"

class SpfTaskInput(BaseModel):
    id: str
    source_task_id: Optional[str] = None
    description: str = ""

class SpfTaskOutput(BaseModel):
    id: str
    type: str
    artifact_path: str
    description: str = ""

class SpfTaskDocument(BaseModel):
    id: str
    type: Literal["task"]
    title: str
    status: str
    component_ids: List[str] = Field(default_factory=list)
    implements_contract_id: Optional[str] = None
    inputs: List[SpfTaskInput] = Field(default_factory=list)
    outputs: List[SpfTaskOutput] = Field(default_factory=list)
    content: str

class SpfEpicManifest(BaseModel):
    id: str
    title: str
    status: str
    type: Literal["spf-epic-manifest"]
    component_ids: List[str]
    abstract: str

class SpfPlanManifest(BaseModel):
    id: str
    title: str
    status: str
    owner: str
    type: Literal["spf-plan-manifest"]
