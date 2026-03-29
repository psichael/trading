import copy
from typing import Dict, Any, List

from mvs_harness.schemas.models import SpfProposal
from mvs_harness.spf_compiler.applicator_actions import (
    apply_creates_components, apply_creates_contracts, 
    apply_creates_epics, apply_creates_tasks,
    apply_updates_tasks
)

def apply_logical_proposal(plan_graph: Dict[str, Any], proposal: SpfProposal) -> Dict[str, Any]:
    """
    Modifies the in-memory plan graph based on the create, update, and
    delete actions in a logical proposal by delegating to specialized action handlers.
    Returns a new, modified graph.
    """
    modified_graph = copy.deepcopy(plan_graph)
    temp_id_map: Dict[str, str] = {}

    def resolve_id(ref_id: str) -> str:
        """
        Resolves a temporary ID to its newly generated UUID, or returns the original ID.
        """
        return temp_id_map.get(ref_id, ref_id)

    def resolve_ids(ref_ids: List[str]) -> List[str]:
        """
        Resolves a list of temporary IDs.
        """
        return [resolve_id(rid) for rid in ref_ids]

    # The order of operations is critical to resolve dependencies correctly.
    # Deletes -> Updates -> Creations (in dependency order).

    # --- 1. Handle Deletions FIRST ---
    if proposal.delete:
        # TODO: Implement deletion logic in applicator_actions.py
        pass

    # --- 2. Handle Updates SECOND ---
    if proposal.update:
        if proposal.update.tasks:
            apply_updates_tasks(modified_graph, proposal.update.tasks)
        # TODO: Implement update logic for components, contracts, epics
        pass

    # --- 3. Handle Creations THIRD ---
    if proposal.create:
        # 3.1. Components are the top-level entities.
        if proposal.create.components:
            apply_creates_components(modified_graph, proposal.create.components, temp_id_map, resolve_id)
        
        # 3.2. Contracts depend on components.
        if proposal.create.contracts:
            apply_creates_contracts(modified_graph, proposal.create.contracts, temp_id_map, resolve_id)
            
        # 3.3. Epics depend on components.
        if proposal.create.epics:
            apply_creates_epics(modified_graph, proposal.create.epics, temp_id_map, resolve_ids)
            
        # 3.4. Tasks depend on epics, contracts, and other tasks.
        if proposal.create.tasks:
            apply_creates_tasks(modified_graph, proposal.create.tasks, temp_id_map, resolve_id, resolve_ids)

    return modified_graph