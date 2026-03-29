import uuid
from typing import Dict, Any, List, Callable
from collections import defaultdict

from mvs_harness.schemas.models import CreateTask, CreateEpic, CreateContract, CreateComponent, UpdateTask
from mvs_harness.schemas.spf_plan_models import (
    SpfEpicManifest, SpfTaskDocument, SpfTaskInput, SpfTaskOutput, SpfComponentManifest, SpfContractDefinition
)

# --- Create Actions --- 

def _topologically_sort_new_tasks(new_tasks: List[CreateTask], temp_id_map: Dict[str, str]) -> List[CreateTask]:
    """Sorts a list of new tasks based on their 'insert_after_task_id' dependencies."""
    task_map: Dict[str, CreateTask] = {task.temp_id: task for task in new_tasks}
    adj: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = {task.temp_id: 0 for task in new_tasks}

    for task in new_tasks:
        if not task.insert_after_task_id:
            continue
        
        if task.insert_after_task_id in task_map:
            predecessor_temp_id = task.insert_after_task_id
            adj[predecessor_temp_id].append(task.temp_id)
            in_degree[task.temp_id] += 1
            
    queue = [task.temp_id for task in new_tasks if in_degree[task.temp_id] == 0]
    sorted_order: List[str] = []
    
    while queue:
        u = queue.pop(0)
        sorted_order.append(u)
        for v in adj.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if len(sorted_order) != len(new_tasks):
        unvisited = set(task_map.keys()) - set(sorted_order)
        raise ValueError(f"A cycle was detected among the new tasks' insertion order, involving: {unvisited}")
        
    return [task_map[tid] for tid in sorted_order]

def apply_creates_components(
    graph: Dict[str, Any], 
    components: List[CreateComponent], 
    temp_id_map: Dict[str, str],
    resolve_id: Callable[[str], str]
):
    if "components" not in graph:
        graph["components"] = {}
    for comp_data in components:
        new_id = str(uuid.uuid4())
        temp_id_map[comp_data.temp_id] = new_id
        new_comp = SpfComponentManifest(
            id=new_id,
            title=comp_data.title,
            parent_component_id=resolve_id(comp_data.parent_component_id),
            abstract=comp_data.abstract
        )
        graph["components"][new_id] = {"manifest": new_comp, "path": ""}

def apply_creates_contracts(
    graph: Dict[str, Any], 
    contracts: List[CreateContract], 
    temp_id_map: Dict[str, str],
    resolve_id: Callable[[str], str]
):
    if "contracts" not in graph:
        graph["contracts"] = {}
    for contract_data in contracts:
        new_id = str(uuid.uuid4())
        temp_id_map[contract_data.temp_id] = new_id
        new_contract = SpfContractDefinition(
            id=new_id,
            title=contract_data.title,
            parent_component_id=resolve_id(contract_data.parent_component_id),
            version=contract_data.version,
            abstract=contract_data.abstract,
            input_schema=contract_data.input_schema if contract_data.input_schema else {},
            output_schema=contract_data.output_schema if contract_data.output_schema else {}
        )
        graph["contracts"][new_id] = {"doc": new_contract, "path": ""}

def apply_creates_epics(
    graph: Dict[str, Any], 
    epics: List[CreateEpic], 
    temp_id_map: Dict[str, str],
    resolve_ids: Callable[[List[str]], List[str]]
):
    if "epics" not in graph:
        graph["epics"] = {}
    for epic_data in epics:
        new_id = str(uuid.uuid4())
        temp_id_map[epic_data.temp_id] = new_id
        new_epic = SpfEpicManifest(
            id=new_id, title=epic_data.title, status="ready",
            type="spf-epic-manifest", component_ids=resolve_ids(epic_data.component_ids),
            abstract=epic_data.abstract
        )
        graph["epics"][new_id] = {"manifest": new_epic, "tasks": [], "path": ""}

def apply_creates_tasks(
    graph: Dict[str, Any], 
    tasks: List[CreateTask], 
    temp_id_map: Dict[str, str],
    resolve_id: Callable[[str], str],
    resolve_ids: Callable[[List[str]], List[str]]
):
    tasks_by_epic: Dict[str, List[CreateTask]] = defaultdict(list)
    for task_data in tasks:
        resolved_epic_id = resolve_id(task_data.parent_epic_id)
        tasks_by_epic[resolved_epic_id].append(task_data)

    for epic_id, new_tasks_for_epic in tasks_by_epic.items():
        if epic_id not in graph.get("epics", {}):
            raise ValueError(f"Parent epic '{epic_id}' not found for new tasks.")
        
        sorted_new_tasks = _topologically_sort_new_tasks(new_tasks_for_epic, temp_id_map)
        epic_task_list: List[Dict[str, Any]] = graph["epics"][epic_id]["tasks"]
        
        for task_data in sorted_new_tasks:
            new_id = str(uuid.uuid4())
            temp_id_map[task_data.temp_id] = new_id
            new_task_doc = SpfTaskDocument(
                id=new_id, type="task", title=task_data.title, status="pending",
                component_ids=resolve_ids(task_data.component_ids),
                implements_contract_id=resolve_id(task_data.implements_contract_id),
                inputs=[SpfTaskInput(id=i.id, source_task_id=resolve_id(i.source_task_id)) for i in (task_data.inputs or [])],
                outputs=[SpfTaskOutput(**o.model_dump()) for o in (task_data.outputs or [])],
                content=task_data.content
            )
            new_task_item = {"doc": new_task_doc, "path": None}

            if task_data.insert_after_task_id:
                insert_after_id = resolve_id(task_data.insert_after_task_id)
                target_index = -1
                for i, existing_task_item in enumerate(epic_task_list):
                    if existing_task_item['doc'].id == insert_after_id:
                        target_index = i
                        break
                if target_index == -1:
                        raise ValueError(f"Task '{insert_after_id}' not found to insert after.")
                epic_task_list.insert(target_index + 1, new_task_item)
            else:
                epic_task_list.insert(0, new_task_item)

# --- Update Actions ---

def _reorder_task_list(task_list: List[Dict[str, Any]], updates: List[UpdateTask]) -> List[Dict[str, Any]]:
    """Reorders a task list based on 'insert_after_task_id' instructions in update proposals."""
    task_map = {item['doc'].id: item for item in task_list}
    moves = {u.id: u.insert_after_task_id for u in updates if u.insert_after_task_id is not None}

    if not moves:
        return task_list

    # This is a simplified reordering logic. For complex chained moves, a topological sort would be more robust.
    # However, for typical UI-driven moves (one or two at a time), this is sufficient.
    reordered_list = [t for t in task_list if t['doc'].id not in moves]
    moved_tasks = {m: task_map[m] for m in moves}

    # Iteratively place moved tasks until all are placed
    while moved_tasks:
        placed_this_iteration = []
        for task_id, target_id in moves.items():
            if task_id not in moved_tasks:
                continue # Already placed
            
            # Find the target's index in the current reordered list
            target_index = -1
            for i, item in enumerate(reordered_list):
                if item['doc'].id == target_id:
                    target_index = i
                    break
            
            if target_index != -1:
                reordered_list.insert(target_index + 1, moved_tasks[task_id])
                placed_this_iteration.append(task_id)
        
        if not placed_this_iteration:
            raise ValueError(f"Could not resolve task reordering. Circular or missing dependency for tasks: {list(moved_tasks.keys())}")

        for task_id in placed_this_iteration:
            del moved_tasks[task_id]

    return reordered_list

def apply_updates_tasks(
    graph: Dict[str, Any], 
    tasks_updates: List[UpdateTask]
):
    task_map: Dict[str, Dict[str, Any]] = {}
    for epic in graph.get("epics", {}).values():
        for task_item in epic.get("tasks", []):
            task_map[task_item['doc'].id] = task_item

    # Group updates by epic for reordering pass
    updates_by_epic: Dict[str, List[UpdateTask]] = defaultdict(list)
    for task_update in tasks_updates:
        if task_update.id not in task_map:
            raise ValueError(f"Task '{task_update.id}' not found for update.")
        
        # Apply content changes
        task_doc_to_update = task_map[task_update.id]['doc']
        update_data = task_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(task_doc_to_update, key):
                setattr(task_doc_to_update, key, value)
        
        for epic_id, epic_content in graph.get("epics", {}).items():
            if any(t['doc'].id == task_update.id for t in epic_content.get("tasks", [])):
                updates_by_epic[epic_id].append(task_update)
                break
    
    # Apply reordering per epic
    for epic_id, epic_updates in updates_by_epic.items():
        current_task_list = graph["epics"][epic_id]["tasks"]
        graph["epics"][epic_id]["tasks"] = _reorder_task_list(current_task_list, epic_updates)