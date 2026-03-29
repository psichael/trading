import typer
import json
from pathlib import Path
from pydantic import ValidationError
from typing import Optional
import jsonschema

from mvs_harness.cli.triage_orchestrator import handle_proposal_execution
from mvs_harness.cli.cycle_logic import assemble_orchestrator_prompt_logic

cycle_app = typer.Typer(help="Commands for the Orchestration and Execution turns.")

@cycle_app.command("start", help="Assembles a JSON prompt for the Orchestrator.")
def cycle_start(
    output_path: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Path to save the output JSON file. Defaults to project_state.json in the project root."
    ),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="The root directory of the project."
    )
):
    try:
        if output_path is None:
            output_path = project_root / "project_state.json"

        assemble_orchestrator_prompt_logic(project_root, output_path)

    except typer.Exit as e:
        raise e
    except Exception as e:
        typer.echo(f"An unexpected error occurred during prompt assembly: {e}", err=True)
        raise typer.Exit(code=1)


@cycle_app.command("execute", help="Validates and executes a Proposal JSON file.")
def cycle_execute(
    proposal_path: Path = typer.Option(
        ...,
        "--proposal", "-p",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the Proposal JSON file."
    ),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="The root directory of the project."
    )
):
    try:
        proposal_data = json.loads(proposal_path.read_text())

        # Delegate all execution logic, including validation and triage, to the orchestrator
        handle_proposal_execution(proposal_data, project_root)

        # Clear the proposal file only if the execution was standard (not a triage)
        if "plan_update_request" not in proposal_data:
            typer.echo(f"Clearing consumed proposal file: {proposal_path}", err=True)
            proposal_path.write_text("")

    except (json.JSONDecodeError, ValidationError, jsonschema.ValidationError) as e:
        typer.secho(f"SCHEMA_ERROR: The proposal is invalid.", fg=typer.colors.RED, err=True)
        
        details = str(e)
        if isinstance(e, ValidationError):
            error_messages = []
            for error in e.errors():
                if error['type'] == 'missing':
                    field_name = error['loc'][-1]
                    error_messages.append(f"'{field_name}' is a required property")
            if error_messages:
                details = "; ".join(error_messages)

        typer.secho(f"Details: {details}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except typer.Exit as e:
        raise e
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
