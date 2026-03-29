# mvs_harness/schemas/spf_legacy_models.py
"""
Pydantic models for the Structured Planning Framework (SPF) v1.0.

These models define the schema for plan, epic, and task manifest files
as specified in the planning-framework-spec-v1.
"""
from __future__ import annotations
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    """Defines an input artifact required by a task."""
    id: str
    source_task_id: str
    description: str


class TaskOutput(BaseModel):
    """Defines an output artifact produced by a task."""
    id: str
    description: str
    type: str
    artifact_path: str


class TaskDocument(BaseModel):
    """Schema for a task document file (e.g., 't001_my-task.doc.yaml')."""
    id: str
    title: str
    status: str
    component_ids: List[str] = Field(default_factory=list)
    inputs: List[TaskInput] = Field(default_factory=list)
    outputs: List[TaskOutput] = Field(default_factory=list)
    content: str


class EpicManifest(BaseModel):
    """Schema for an epic manifest file ('_epic.manifest.yaml')."""
    id: str
    title: str
    status: str
    component_ids: List[str] = Field(default_factory=list)
    abstract: str


class PlanComponent(BaseModel):
    """Defines a high-level component within a plan."""
    id: str
    type: str
    abstract: str


class PlanEpicRef(BaseModel):
    """A reference to an epic within a plan."""
    epic_id: str


class PlanManifest(BaseModel):
    """Schema for a plan manifest file ('_plan.manifest.yaml')."""
    id: str
    title: str
    status: str
    owner: str
    components: List[PlanComponent] = Field(default_factory=list)
    epics: List[PlanEpicRef] = Field(default_factory=list)
