# mvs_harness/spf_parser.py
"""
Parser for the Structured Planning Framework (SPF).

This module reads a directory structure conforming to the SPF specification
and loads it into a validated, hierarchical Pydantic object model.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ValidationError

from .schemas.spf_legacy_models import EpicManifest, PlanManifest, TaskDocument


class SPFValidationError(ValueError):
    """Custom exception for errors during SPF parsing and validation."""

    def __init__(self, message: str, file_path: Path | None = None):
        self.file_path = file_path
        if file_path:
            super().__init__(f"{message} in file: {file_path}")
        else:
            super().__init__(message)

# Internal models to represent the hierarchical structure of the plan graph

class SPFTask(BaseModel):
    """Represents a parsed task document within the plan graph."""
    path: Path
    data: TaskDocument


class SPFEpic(BaseModel):
    """Represents a parsed epic, including its manifest and child tasks."""
    path: Path
    manifest: EpicManifest
    tasks: List[SPFTask] = []


class SPFPlan(BaseModel):
    """Represents the root of the parsed plan graph."""
    path: Path
    manifest: PlanManifest
    epics: List[SPFEpic] = []


def load_plan(plan_dir: Path) -> SPFPlan:
    """
    Loads an entire plan from a directory structured according to the SPF specification.

    Args:
        plan_dir: The root path of the plan/ directory.

    Returns:
        An SPFPlan object representing the entire validated plan graph.

    Raises:
        SPFValidationError: If the plan structure or file contents are invalid.
    """
    if not plan_dir.is_dir():
        raise SPFValidationError(f"Plan directory not found: {plan_dir}")

    # 1. Parse the root plan manifest (if it exists)
    plan_manifest_path = plan_dir / "_plan.manifest.yaml"
    if not plan_manifest_path.is_file():
        # If the root manifest is missing, create a default one to allow epic discovery to proceed.
        plan_manifest = PlanManifest(
            id="default-plan",
            title="Default Plan",
            status="active",
            owner="unknown",
        )
    else:
        try:
            with plan_manifest_path.open("r", encoding="utf-8") as f:
                plan_data = yaml.safe_load(f)
            plan_manifest = PlanManifest.model_validate(plan_data)
        except (yaml.YAMLError, ValidationError) as e:
            raise SPFValidationError(f"Failed to parse plan manifest: {e}", plan_manifest_path) from e

    plan = SPFPlan(path=plan_dir, manifest=plan_manifest)

    # 2. Discover and parse epics and their tasks
    for epic_dir in sorted(plan_dir.iterdir()):
        if not epic_dir.is_dir():
            continue

        epic_manifest_path = epic_dir / "_epic.manifest.yaml"
        if not epic_manifest_path.is_file():
            # Skip directories that don't contain an epic manifest
            continue

        try:
            with epic_manifest_path.open("r", encoding="utf-8") as f:
                epic_data = yaml.safe_load(f)
            epic_manifest = EpicManifest.model_validate(epic_data)
        except (yaml.YAMLError, ValidationError) as e:
            raise SPFValidationError(f"Failed to parse epic manifest: {e}", epic_manifest_path) from e

        epic = SPFEpic(path=epic_dir, manifest=epic_manifest)

        # 3. Parse tasks within the epic
        for task_file in sorted(epic_dir.glob("*.doc.yaml")):
            if not task_file.is_file():
                continue
            try:
                with task_file.open("r", encoding="utf-8") as f:
                    task_data = yaml.safe_load(f)
                task_doc = TaskDocument.model_validate(task_data)
                epic.tasks.append(SPFTask(path=task_file, data=task_doc))
            except (yaml.YAMLError, ValidationError) as e:
                raise SPFValidationError(f"Failed to parse task document: {e}", task_file) from e

        plan.epics.append(epic)

    return plan
