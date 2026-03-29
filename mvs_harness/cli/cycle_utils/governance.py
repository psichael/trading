import typer
import yaml
from pathlib import Path
from typing import Optional

from mvs_harness.schemas.models import Proposal, Command

def get_epic_propagation_proposal(completed_task_path: Optional[str], project_root: Path) -> Optional[Proposal]:
    """
    Checks if an epic can be marked as completed. If so, returns a new proposal.
    """
    if not completed_task_path:
        return None

    typer.echo("Checking for epic status propagation...", err=True)
    task_path = project_root / completed_task_path
    epic_path = task_path.parent
    manifest_path = epic_path / "_topic.manifest.yaml"
    relative_epic_path = epic_path.relative_to(project_root)

    if not manifest_path.is_file():
        typer.echo(f"  - No epic manifest found at '{relative_epic_path}'. Skipping propagation.", err=True)
        return None
    
    try:
        manifest_data = yaml.safe_load(manifest_path.read_text())
        if manifest_data.get("status") == "completed":
            typer.echo(f"  - Epic '{relative_epic_path}' is already completed. Skipping.", err=True)
            return None
    except (yaml.YAMLError, IOError) as e:
        typer.secho(f"  - Error reading epic manifest {manifest_path.relative_to(project_root)}: {e}", fg=typer.colors.RED, err=True)
        return None

    all_tasks_completed = True
    task_files_found = 0
    for item in epic_path.glob("*.doc.yaml"):
        task_files_found += 1
        try:
            task_data = yaml.safe_load(item.read_text())
            status = task_data.get("status", "pending")
            if status not in ["completed", "finalized"]:
                all_tasks_completed = False
                typer.echo(f"  - Epic not complete: Task '{item.relative_to(project_root)}' has status '{status}'.", err=True)
                break
        except (yaml.YAMLError, AttributeError) as e:
            typer.echo(f"  - Warning: Could not parse task file {item.relative_to(project_root)}: {e}", err=True)
            all_tasks_completed = False
            break

    if task_files_found == 0:
        typer.echo("  - No task files found in epic. Skipping propagation.", err=True)
        return None

    if all_tasks_completed:
        typer.secho(f"  - All tasks in epic '{relative_epic_path}' are completed. Generating propagation proposal.", fg=typer.colors.GREEN, err=True)
        
        manifest_data["status"] = "completed"
        new_manifest_content = yaml.dump(manifest_data, indent=2, default_flow_style=False)
        
        return Proposal(
            plan_analysis="Automated governance: All child tasks of this epic are completed. This proposal updates the epic's status to 'completed'.",
            summary=f"chore(plan): Mark epic '{relative_epic_path}' as completed",
            event_type="chore",
            commands=[
                {
                    "command": "update_file",
                    "path": str(manifest_path.relative_to(project_root)),
                    "content": new_manifest_content
                }
            ]
        )
    return None

def inject_task_completion_command_if_needed(proposal: Proposal, project_root: Path):
    """
    If a proposal completes a task, this function injects a command at the
    start of the command list to ensure the task's status is updated on disk.
    """
    if not proposal.completed_task_path:
        return

    task_file_rel_path = proposal.completed_task_path
    typer.echo(f"  - Governance: Auto-updating status for completed task '{task_file_rel_path}'", err=True)
    task_file_abs_path = project_root / task_file_rel_path
    
    if task_file_abs_path.is_file():
        try:
            task_data = yaml.safe_load(task_file_abs_path.read_text(encoding='utf-8'))
            if isinstance(task_data, dict) and task_data.get("status") != "completed":
                task_data["status"] = "completed"
                updated_content = yaml.dump(task_data, indent=2, default_flow_style=False)
                
                update_command = Command(
                    command="update_file",
                    path=task_file_rel_path,
                    content=updated_content
                )
                proposal.commands.insert(0, update_command)
                typer.echo(f"    - Injected command to mark task as completed.", err=True)
        except (yaml.YAMLError, IOError) as e:
            typer.secho(f"    - WARNING: Could not auto-update task status for {task_file_rel_path}: {e}", fg=typer.colors.YELLOW, err=True)
    else:
        typer.secho(f"    - WARNING: Completed task file not found at '{task_file_rel_path}'. Cannot auto-update status.", fg=typer.colors.YELLOW, err=True)
