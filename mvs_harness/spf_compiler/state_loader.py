from pathlib import Path
from typing import Dict, Any
import yaml

from mvs_harness.schemas.spf_plan_models import (
    SpfPlanManifest, SpfEpicManifest, SpfTaskDocument
)

def load_plan_state_from_fs(plan_root: Path) -> Dict[str, Any]:
    """
    Parses the current SDF3 plan from the filesystem into a structured, in-memory
    graph representation. If the plan doesn't exist, it returns a default empty state
    with a valid in-memory plan manifest. Tasks are loaded into an ordered list
    of dictionaries, each containing the document and its original path.
    """
    plan_state: Dict[str, Any] = {
        "plan": None,
        "epics": {},
    }

    if not plan_root.is_dir():
        plan_root.mkdir()

    # 1. Parse or create the root plan manifest
    plan_manifest_path = plan_root / "_topic.manifest.yaml"
    if plan_manifest_path.is_file():
        with plan_manifest_path.open("r") as f:
            plan_data = yaml.safe_load(f)
            plan_manifest = SpfPlanManifest.model_validate(plan_data)
    else:
        # If no plan exists, create a default in-memory manifest to ensure
        # the graph structure is always consistent.
        plan_manifest = SpfPlanManifest(
            id="temp-plan-id",
            title="New Project Plan",
            status="proposed",
            owner="planner-agent@1.0",
            type="spf-plan-manifest"
        )
    plan_state["plan"] = plan_manifest

    # 2. Discover and parse epics and their tasks
    for epic_dir in sorted(plan_root.iterdir()):
        if not epic_dir.is_dir():
            continue

        epic_manifest_path = epic_dir / "_topic.manifest.yaml"
        if not epic_manifest_path.is_file():
            continue
        
        with epic_manifest_path.open("r") as f:
            epic_data = yaml.safe_load(f)
            epic_manifest = SpfEpicManifest.model_validate(epic_data)
        
        epic_id = epic_manifest.id
        plan_state["epics"][epic_id] = {
            "manifest": epic_manifest,
            "tasks": [],
            "path": str(epic_dir.relative_to(plan_root.parent))
        }

        # 3. Parse tasks within the epic, preserving order and path
        for task_file in sorted(epic_dir.glob("*.doc.yaml")):
            if not task_file.is_file():
                continue
            
            with task_file.open("r") as f:
                task_data = yaml.safe_load(f)
            
            if task_data.get("type") == "task":
                task_doc = SpfTaskDocument.model_validate(task_data)
                task_path = str(task_file.relative_to(plan_root.parent))
                plan_state["epics"][epic_id]["tasks"].append({"doc": task_doc, "path": task_path})

    return plan_state
