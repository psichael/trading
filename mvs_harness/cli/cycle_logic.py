import typer
from pathlib import Path
from typing import Optional, Dict, Any

from mvs_harness.schemas.models import Proposal, OrchestratorPrompt
from mvs_harness.cli import sdf_renumbering
from mvs_harness.cli.cycle_utils import (
    command_executor, event_logger, git_committer, governance, state_manager, 
    prompt_builder, sdf_compiler, validation, proposal_dispatcher, triage_handler
)

def assemble_orchestrator_prompt_logic(project_root: Path, output_path: Path):
    """Orchestrates the assembly of the OrchestratorPrompt."""
    sdf_compiler.compile_sdf_specs(project_root)
    
    typer.echo("Assembling Orchestrator prompt...", err=True)
    project_state = state_manager.load_project_state_for_orchestrator(project_root)
    governing_protocol = prompt_builder.load_orchestrator_protocol(project_root)

    injected_files = project_state.context_files
    project_state.context_files = []

    orchestrator_prompt = OrchestratorPrompt(
        governing_protocol=governing_protocol,
        project_state=project_state,
        injected_context_files=injected_files
    )
    prompt_builder.write_orchestrator_prompt_to_file(orchestrator_prompt, output_path)
    typer.echo("Orchestrator prompt assembly complete.\n", err=True)

def execute_proposal_logic(initial_proposal_data: Dict[str, Any], project_root: Path):
    """Orchestrates the execution of a proposal and any subsequent auto-generated proposals."""
    typer.echo("Proposal execution cycle started.", err=True)

    # --- Dispatch & Validation Step ---
    # Convert the raw proposal data (logical or direct) into a standard command-based proposal.
    initial_proposal = proposal_dispatcher.prepare_proposal_for_execution(
        initial_proposal_data, project_root
    )

    # --- Triage Check ---
    # If the proposal is a plan update request, handle it and stop the execution cycle.
    if initial_proposal.plan_update_request:
        triage_handler.handle_plan_update_request(initial_proposal, project_root)
        event_logger.log_proposal_event(initial_proposal, project_root)
        # Note: We do not commit a triage request itself, as it's a meta-operation.
        # The Planner's subsequent proposal will be committed.
        return # Exit early

    # --- Execution Loop ---
    current_proposal: Optional[Proposal] = initial_proposal

    while current_proposal is not None:
        typer.echo(f"\nExecuting proposal: {current_proposal.summary}", err=True)

        governance.inject_task_completion_command_if_needed(current_proposal, project_root)

        # validation.validate_sdf_changes(current_proposal, project_root) # <-- TEMPORARILY DISABLED
        command_executor.execute_proposal_commands(current_proposal, project_root)

        sdf_renumbering.renumber_sdf_directories_if_needed(current_proposal, project_root)

        event_logger.log_proposal_event(current_proposal, project_root)
        git_committer.commit_changes(current_proposal, project_root)

        next_proposal = governance.get_epic_propagation_proposal(current_proposal.completed_task_path, project_root)
        current_proposal = next_proposal

    state_manager.update_context_manifest(project_root)
    typer.echo("\nProposal execution cycle complete.", err=True)
