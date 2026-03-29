import typer
import json
import yaml
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from pydantic import ValidationError

from mvs_harness.planner import assemble_project_state
from mvs_harness.schemas.models import ContextManifest, ProjectState
from mvs_harness.schemas.spf_plan_models import SpfTaskDocument

def find_next_task(plan_root: Path) -> Optional[Tuple[Path, Dict[str, Any]]]:
    """
    Finds the next task to be executed. It prioritizes any task that is already
    'active'. If no active task is found, it returns the first 'pending' task
    it discovers in lexicographical order.
    """
    if not plan_root.is_dir():
        return None

    active_task: Optional[Tuple[Path, Dict[str, Any]]] = None
    first_pending_task: Optional[Tuple[Path, Dict[str, Any]]] = None

    for epic_dir in sorted(plan_root.iterdir()):
        if not epic_dir.is_dir():
            continue

        if not (epic_dir / "_topic.manifest.yaml").is_file() and not (epic_dir / "_epic.manifest.yaml").is_file():
            continue

        for task_file in sorted(epic_dir.glob("*.doc.yaml")):
            if not task_file.is_file():
                continue

            try:
                with task_file.open("r") as f:
                    task_data = yaml.safe_load(f)

                if isinstance(task_data, dict):
                    SpfTaskDocument.model_validate(task_data)
                    status = task_data.get("status")
                    if status == "active":
                        # An active task always takes precedence. Stop searching and return immediately.
                        return task_file, task_data
                    elif status == "pending" and first_pending_task is None:
                        # Found the first pending task. Hold onto it and keep looking for an active one.
                        first_pending_task = (task_file, task_data)
            except (yaml.YAMLError, ValidationError):
                continue

    # If we finished the loop without finding an active task, return the first pending one we saw.
    return first_pending_task


def update_context_manifest(project_root: Path):
    """Finds the next task and updates/removes the .ddio/context_manifest.json."""
    typer.echo("Updating context manifest for next cycle...", err=True)
    next_task_info = find_next_task(project_root / "plan")
    context_manifest_path = project_root / ".ddio/context_manifest.json"
    if next_task_info:
        task_path, task_data = next_task_info
        manifest = ContextManifest(
            active_task=str(task_path.relative_to(project_root)),
            task_content=task_data.get('content', '')
        )
        context_manifest_path.parent.mkdir(exist_ok=True)
        context_manifest_path.write_text(manifest.model_dump_json(indent=2))
        typer.echo(f"Wrote new context manifest for task: {manifest.active_task}", err=True)
    else:
        if context_manifest_path.exists():
            context_manifest_path.unlink()
        typer.echo("Project complete or no more ready tasks. Context manifest removed.", err=True)

def load_project_state_for_orchestrator(project_root: Path) -> ProjectState:
    """Loads the project state, potentially from a context manifest or by discovering the active task."""
    context_manifest_path = project_root / ".ddio/context_manifest.json"
    if context_manifest_path.exists() and context_manifest_path.is_file():
        typer.echo("Context manifest found. Starting execution cycle.", err=True)
        manifest_data = json.loads(context_manifest_path.read_text())
        manifest = ContextManifest.model_validate(manifest_data)
        project_state = assemble_project_state(project_root=project_root, override_task=manifest)
    else:
        typer.echo("No context manifest. Starting planning/discovery cycle.", err=True)
        project_state = assemble_project_state(project_root=project_root)

    if not project_state.active_task:
        typer.secho("No active or pending tasks found. Planning may be required.", fg=typer.colors.YELLOW, err=True)
        typer.echo("Hint: Run 'ddio plan start' to generate a new plan.", err=True)
        raise typer.Exit(code=1)
    return project_state
