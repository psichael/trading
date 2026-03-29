from pathlib import Path
from typing import List

from mvs_harness.schemas.models import SpfProposal, Command
from . import state_loader, proposal_applicator, graph_validator, command_generator


class SpfCompiler:
    """
    Orchestrates the process of applying a logical plan proposal to the filesystem.
    """

    def __init__(self, plan_root: Path):
        self.plan_root = plan_root

    def compile_and_validate(self, proposal: SpfProposal) -> List[Command]:
        """
        Loads the current state, applies the proposal, validates the result,
        and generates filesystem commands.
        """
        # 1. Load current state from filesystem
        initial_state = state_loader.load_plan_state_from_fs(self.plan_root)

        # 2. Apply logical changes to the in-memory state
        modified_state = proposal_applicator.apply_logical_proposal(initial_state, proposal)

        # 3. Validate the resulting state
        errors = graph_validator.validate_plan_graph(modified_state)
        if errors:
            raise ValueError(f"Plan validation failed: {'; '.join(errors)}")

        # 4. Generate filesystem commands based on the diff
        commands = command_generator.generate_fs_commands(initial_state, modified_state)

        return commands
