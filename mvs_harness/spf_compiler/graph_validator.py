from typing import Dict, Any, List, Set, Iterable

from mvs_harness.schemas.spf_plan_models import SpfTaskDocument

def validate_plan_graph(plan_graph: Dict[str, Any]) -> List[str]:
    """
    Performs validation on the in-memory graph where tasks are in an ordered list,
    checking for circular dependencies (DAG check) and referential integrity.
    """
    errors: List[str] = []
    all_tasks_map: Dict[str, SpfTaskDocument] = {}

    def get_task_iterator(epic_content: Dict[str, Any]) -> Iterable[SpfTaskDocument]:
        """Helper to handle new list-of-dicts, raw lists, and old dict task formats."""
        tasks_container = epic_content.get("tasks", [])
        if isinstance(tasks_container, dict): # Handles old test format: {"id": SpfTaskDocument}
            yield from tasks_container.values()
        elif isinstance(tasks_container, list):
            for item in tasks_container:
                if isinstance(item, dict) and 'doc' in item: # New format: {"doc": ..., "path": ...}
                    yield item['doc']
                elif isinstance(item, SpfTaskDocument): # Handles raw list of task docs
                    yield item

    # Collect all tasks into a map for efficient lookup
    for epic in plan_graph.get("epics", {}).values():
        for task in get_task_iterator(epic):
            all_tasks_map[task.id] = task

    # 1. Referential Integrity Check
    for task in all_tasks_map.values():
        for task_input in task.inputs:
            if not task_input.source_task_id:
                continue

            source_task = all_tasks_map.get(task_input.source_task_id)
            if not source_task:
                errors.append(
                    f"Task '{task.id}' has an invalid dependency: "
                    f"source_task_id '{task_input.source_task_id}' not found."
                )
                continue # Skip further checks for this broken dependency

            # Check if the source task actually produces the required input
            source_output_ids = {output.id for output in source_task.outputs}
            if task_input.id not in source_output_ids:
                errors.append(
                    f"Task '{task.id}' requests input '{task_input.id}' which is not an "
                    f"output of source task '{task_input.source_task_id}'."
                )

    # 2. Circular Dependency (DAG) Check
    if not errors: # Only check for cycles if references are valid
        adj: Dict[str, List[str]] = {task_id: [] for task_id in all_tasks_map.keys()}
        for task in all_tasks_map.values():
            for task_input in task.inputs:
                if task_input.source_task_id:
                    # A task depends on its input's source
                    adj[task.id].append(task_input.source_task_id)

        visiting: Set[str] = set()
        visited: Set[str] = set()

        def has_cycle(node: str) -> bool:
            visiting.add(node)
            for neighbor in adj.get(node, []):
                if neighbor in visiting:
                    return True  # Cycle detected
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
            visiting.remove(node)
            visited.add(node)
            return False

        for task_id in all_tasks_map.keys():
            if task_id not in visited:
                if has_cycle(task_id):
                    errors.append(
                        f"Circular dependency detected in the plan graph involving task '{task_id}'."
                    )
                    break # Stop after first cycle
    
    return errors
