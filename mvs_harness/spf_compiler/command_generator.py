import re
import yaml
from typing import Dict, Any, List
from pydantic import BaseModel

from mvs_harness.schemas.models import Command
from mvs_harness.schemas.spf_plan_models import SpfEpicManifest, SpfTaskDocument
from mvs_harness.sdf.utils import generate_uuid, slugify


def _model_to_yaml(model: BaseModel) -> str:
    """Serializes a Pydantic model to a YAML string."""
    return yaml.dump(model.model_dump(mode='json'), sort_keys=False, indent=2)

def generate_fs_commands(original_graph: Dict[str, Any], modified_graph: Dict[str, Any]) -> List[Command]:
    """
    Compares the modified in-memory graph with the initial state and generates
    a list of file system commands to reflect creations, updates, and renames.
    """
    commands: List[Command] = []

    # --- Step 1: Handle Epic Creations --- 
    original_epic_ids = set(original_graph.get("epics", {}).keys())
    
    epic_index = len(original_epic_ids)
    epic_id_map: Dict[str, Dict[str, str]] = {} # Maps temp IDs to new UUIDs and paths

    for temp_id, epic_data in modified_graph.get("epics", {}).items():
        if temp_id in original_epic_ids:
            continue # Skip existing epics for creation

        manifest_model = SpfEpicManifest.model_validate(epic_data["manifest"])
        new_uuid = generate_uuid()
        slug = slugify(manifest_model.title)
        manifest_model.id = new_uuid

        dir_name = f"{epic_index:04d}_{new_uuid}_{slug}"
        dir_path = f"plan/{dir_name}"

        epic_id_map[temp_id] = {"uuid": new_uuid, "path": dir_path}

        commands.append(Command(command="create_directory", path=dir_path))
        manifest_content = _model_to_yaml(manifest_model)
        manifest_path = f"{dir_path}/_topic.manifest.yaml"
        commands.append(Command(command="create_file", path=manifest_path, content=manifest_content))
        epic_index += 1

    # --- Step 2: Handle Task Creations, Updates, and Renames (Diff-aware) ---
    for epic_id, epic_content in modified_graph.get("epics", {}).items():
        # Build a map of original tasks from ID to their full path for easy lookup
        original_task_items = original_graph.get("epics", {}).get(epic_id, {}).get("tasks", [])
        original_task_map: Dict[str, Dict[str, Any]] = {item['doc'].id: item for item in original_task_items}
        
        modified_task_items: List[Dict[str, Any]] = epic_content.get("tasks", [])

        if epic_id in epic_id_map: # It's a newly created epic
            epic_dir_path = epic_id_map[epic_id]["path"]
        elif epic_id in original_graph.get("epics", {}): # It's a pre-existing epic
            epic_dir_path = original_graph["epics"][epic_id].get("path", "")
            if not epic_dir_path:
                 raise ValueError(f"Could not find path for existing epic '{epic_id}'")
        else:
            continue

        # Iterate through the final, ordered list of tasks for the epic
        for new_index, task_item in enumerate(modified_task_items):
            task_doc = task_item['doc']
            task_id = task_doc.id

            # Check if this task is new by its (temporary or real) ID
            if task_id not in original_task_map:
                new_uuid = generate_uuid()
                slug = slugify(task_doc.title)
                
                task_doc.id = new_uuid # Assign the real, final UUID

                file_name = f"{new_index:04d}_{new_uuid}_{slug}.doc.yaml"
                file_path = f"{epic_dir_path}/{file_name}"

                task_content = _model_to_yaml(task_doc)
                commands.append(Command(command="create_file", path=file_path, content=task_content))
            else: # This is a pre-existing task
                original_item = original_task_map[task_id]
                original_path = original_item['path']
                original_filename = original_path.split('/')[-1]
                current_path_for_update = original_path
                
                match = re.match(r"(\d+)_.*", original_filename)
                original_index = int(match.group(1)) if match else -1

                # Check for reordering
                if new_index != original_index:
                    # Retain original UUID and slug, just change the index
                    new_filename = re.sub(r"^\d+", f"{new_index:04d}", original_filename)
                    new_path = f"{epic_dir_path}/{new_filename}"
                    commands.append(Command(command="move_file", path=original_path, new_path=new_path))
                    current_path_for_update = new_path
                
                # Check for content updates
                original_content = _model_to_yaml(original_item['doc'])
                modified_content = _model_to_yaml(task_doc)
                if original_content != modified_content:
                    commands.append(Command(
                        command="update_file", 
                        path=current_path_for_update, 
                        content=modified_content
                    ))

    # TODO: Implement diffing logic for deletions.

    return commands
