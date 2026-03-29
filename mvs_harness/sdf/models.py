from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class SdfBaseModel(BaseModel):
    """Base model for common SDF document attributes."""
    id: str
    status: Literal["draft", "finalized", "deprecated"] = "draft"
    tags: List[str] = Field(default_factory=list)

class Doc(SdfBaseModel):
    """Represents a single atomic unit of documentation (.doc.yaml file)."""
    type: str = "paragraph"
    content: str = ""
    references: List[str] = Field(default_factory=list) # Simplified from spec for now

class TopicManifest(SdfBaseModel):
    """Represents the governance manifest for a topic (_topic.manifest.yaml)."""
    title: str
    version: str = "1.0"
    owner: Optional[str] = None
    abstract: str = ""
    relations: List[dict] = Field(default_factory=list) # Simplified from spec

class SdfTopicNode(BaseModel):
    """
    Represents a directory in the SDF structure, containing a manifest,
    child documents, and sub-topics.
    """
    manifest: TopicManifest
    docs: List[Doc] = Field(default_factory=list)
    sub_topics: List[SdfTopicNode] = Field(default_factory=list)

    # A property to easily access the title for directory naming
    @property
    def title(self) -> str:
        return self.manifest.title

# Update forward references
SdfTopicNode.model_rebuild()
