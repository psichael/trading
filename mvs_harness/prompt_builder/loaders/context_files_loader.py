from pathlib import Path
from typing import List

from mvs_harness.schemas.models import WorkOrder, ContextFile

class ContextFileNotFoundError(FileNotFoundError):
    """Custom exception for when a requested context file or directory does not exist."""
    pass

def load_context_files(work_order: WorkOrder, project_root: Path) -> List[ContextFile]:
    """
    Gathers and reads all required context files based on a WorkOrder.

    This function expands directories recursively, ensures the active task file is
    always included, and prevents duplicate file entries. It also unconditionally
    includes critical system-level governance files.

    Args:
        work_order: The WorkOrder containing the list of required file/directory paths.
        project_root: The root directory of the project.

    Returns:
        A list of ContextFile objects.
    
    Raises:
        ContextFileNotFoundError: If a path specified in the work order does not exist.
    """
    context_files: List[ContextFile] = []
    gathered_paths = set()

    # Define unconditional system-level files that must always be in context.
    system_files = [
        'mvs_harness/schemas/proposal.schema.json'
    ]
    
    # Combine system files with files from the work order.
    all_required_paths = system_files + work_order.required_context_files

    # Process all paths
    for req_path_str in all_required_paths:
        full_path = project_root / req_path_str
        if not full_path.exists():
            # For now, let's warn for system files but raise for user-requested files.
            if req_path_str in work_order.required_context_files:
                raise ContextFileNotFoundError(f"Required context path does not exist: {req_path_str}")
            else:
                # Silently skip missing system files
                continue

        if full_path.is_file():
            if req_path_str not in gathered_paths:
                content = full_path.read_text(encoding='utf-8', errors='replace')
                context_files.append(ContextFile(path=req_path_str, content=content))
                gathered_paths.add(req_path_str)

        elif full_path.is_dir():
            for sub_path in sorted(full_path.rglob("*")):
                if "__pycache__" in sub_path.parts or sub_path.name.endswith('.pyc'):
                    continue
                
                if sub_path.is_file():
                    rel_path_str = str(sub_path.relative_to(project_root)).replace("\\", "/")
                    
                    # CRITICAL EXCLUSION: Prevent heavy history/telemetry files from entering context
                    if rel_path_str.startswith('live/data_code/history/'):
                        continue

                    if rel_path_str not in gathered_paths:
                        content = sub_path.read_text(encoding='utf-8', errors='replace')
                        context_files.append(ContextFile(path=rel_path_str, content=content))
                        gathered_paths.add(rel_path_str)
    
    # CRITICAL: Always ensure the active task file itself is included in the context.
    active_task_path_str = work_order.active_task
    if active_task_path_str and active_task_path_str not in gathered_paths:
        active_task_full_path = project_root / active_task_path_str
        if active_task_full_path.is_file():
            content = active_task_full_path.read_text(encoding='utf-8', errors='replace')
            context_files.append(ContextFile(path=active_task_path_str, content=content))

    return context_files