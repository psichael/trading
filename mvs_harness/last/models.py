from __future__ import annotations
from typing import List, Literal, Union
from pydantic import BaseModel, Field

class ModuleNode(BaseModel):
    """Represents the root of a LAST tree, equivalent to a Python module."""
    node_type: Literal["module"] = "module"
    body: List[LASTNode] = Field(default_factory=list)

class FunctionDefNode(BaseModel):
    """Represents a function definition."""
    node_type: Literal["function_def"] = "function_def"
    name: str
    args: List[str] = Field(default_factory=list)
    body: List[LASTNode] = Field(default_factory=list)

class PassNode(BaseModel):
    """Represents a 'pass' statement."""
    node_type: Literal["pass"] = "pass"

# A discriminated union of all possible node types.
# This allows Pydantic to automatically select the correct model during parsing.
LASTNode = Union[ModuleNode, FunctionDefNode, PassNode]

# Update forward references in models that use LASTNode recursively.
# This is crucial for Pydantic to build the correct model relationships.
ModuleNode.model_rebuild()
FunctionDefNode.model_rebuild()
