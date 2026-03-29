import yaml
import typer
from pathlib import Path
from typing import Optional, Dict, Any

from mvs_harness.schemas.models import ProjectState, ContextManifest
from mvs_harness.cli.cycle_utils import state_manager
from mvs_harness.state_assembler.file_tree import generate_file_tree
from mvs_harness.state_assembler.event_reader import get_recent_events
from mvs_harness.state_assembler.context_gatherer import gather_context_files

def assemble_project_state(
    project_root: Path,
    override_task: Optional[ContextManifest] = None
) -> ProjectState:
    active_task_path_str: Optional[str] = None
    task_content: str = ""
    task_data: Dict[str, Any] = {}

    # Step 1: Determine the active task path from override or discovery.
    if override_task and override_task.active_task:
        active_task_path_str = override_task.active_task
    else:
        plan_dir = project_root / "plan"
        task_info = state_manager.find_next_task(plan_dir)
        if task_info:
            found_path, found_data = task_info
            active_task_path_str = str(found_path.relative_to(project_root))
            task_data = found_data

            # CRITICAL STATE TRANSITION: If a pending task is found, activate it.
            if task_data.get("status") == "pending":
                typer.secho(f"Activating task: {active_task_path_str}", fg=typer.colors.CYAN, err=True)
                task_data["status"] = "active"
                with found_path.open("w") as f:
                    yaml.dump(task_data, f, sort_keys=False)


    # Step 2: If a task exists, load its full data from disk to get its content
    # and its list of required context files.
    if active_task_path_str:
        try:
            # If we activated a task, task_data is already populated.
            if not task_data:
                full_task_path = project_root / active_task_path_str
                loaded_data = yaml.safe_load(full_task_path.read_text())
                if isinstance(loaded_data, dict):
                    task_data = loaded_data
            
            task_content = task_data.get('content', override_task.task_content if override_task else "")
        except (IOError, yaml.YAMLError, TypeError):
            if override_task:
                task_content = override_task.task_content
            task_data = {}  # Ensure task_data is a dict to prevent errors below.

    # Step 3: UNIFIED Context File Assembly.
    # Start with the INDEPENDENT, UNCONDITIONAL system-level files.
    required_paths = [
        'mvs_harness/schemas/proposal.schema.json'
    ]
    
    # Add the task-specific files.
    task_specific_paths = task_data.get('required_context_files', [])
    required_paths.extend(task_specific_paths)

    # Ensure the active task file itself is always in the context list.
    if active_task_path_str:
        required_paths.append(active_task_path_str)

    # Gather all unique files.
    context_files = gather_context_files(list(set(required_paths)), project_root)
    
    # Step 4: Assemble final state object.
    file_tree_str = generate_file_tree(project_root)
    recent_events_list = get_recent_events(project_root)

    return ProjectState(
        active_task=active_task_path_str,
        active_task_content=task_content,
        recent_events=recent_events_list,
        file_tree=file_tree_str,
        context_files=context_files
    )
