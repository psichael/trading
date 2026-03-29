import json
import jsonschema
from pathlib import Path
from typing import Dict, Any
import typer
import referencing
import referencing.exceptions
from referencing.jsonschema import DRAFT7
import pyperclip # <-- ADDED IMPORT

from mvs_harness.schemas.models import Proposal
from mvs_harness.spf_compiler.compiler import SpfCompiler


def _create_schema_validator(project_root: Path) -> jsonschema.Draft7Validator:
    """Creates a schema validator that can resolve local file-based $refs."""
    schemas_dir = project_root / "mvs_harness" / "schemas"
    if not schemas_dir.is_dir():
        raise FileNotFoundError(f"Schemas directory not found at '{schemas_dir}'")

    # Create a registry containing all schemas, identified by their absolute file URIs.
    resources = [
        (
            f.as_uri(),
            DRAFT7.create_resource(json.loads(f.read_text()))
        )
        for f in schemas_dir.rglob("*.json")
    ]
    registry = referencing.Registry().with_resources(resources)

    # Load the main schema and inject an '$id' to serve as the base URI.
    # This is crucial for the validator to resolve relative '$ref' paths correctly.
    main_schema_path = schemas_dir / "proposal.schema.json"
    main_schema_contents = json.loads(main_schema_path.read_text())
    main_schema_contents["$id"] = main_schema_path.as_uri()

    return jsonschema.Draft7Validator(main_schema_contents, registry=registry)


def prepare_proposal_for_execution(
    proposal_data: Dict[str, Any],
    project_root: Path
) -> Proposal:
    """
    Validates a raw proposal and, if it's a logical plan, compiles it into a
    standard, command-based Proposal object.
    """
    typer.echo("Validating proposal against unified 'proposal.schema.json'...", err=True)
    try:
        validator = _create_schema_validator(project_root)
        validator.validate(proposal_data)
    except jsonschema.ValidationError as e:
        typer.secho("SCHEMA_ERROR: The proposal is invalid.", fg=typer.colors.RED, err=True)
        typer.secho(f"  - Details: {e.message}", fg=typer.colors.RED, err=True)
        typer.secho(f"  - Path: {list(e.path)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    except referencing.exceptions.Unresolvable as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    
    proposal = Proposal.model_validate(proposal_data)

    # NEW: Handle context requests. This is a terminal action.
    if proposal.context_request:
        typer.echo("Context request detected. Gathering file contents...", err=True)
        all_content = []
        for file_path_str in proposal.context_request.requested_files:
            file_path = project_root / file_path_str
            header = f"""
# ======================================================================================
# File: {file_path_str}
# ======================================================================================
"""
            all_content.append(header)
            if file_path.is_file():
                all_content.append(file_path.read_text())
            else:
                typer.secho(f"  - WARNING: Requested file not found: {file_path_str}", fg=typer.colors.YELLOW, err=True)
                all_content.append(f"### ERROR: File not found at '{file_path_str}' ###")

        full_context = "\n".join(all_content)
        pyperclip.copy(full_context)
        typer.secho("Success! Requested context has been copied to the clipboard.", fg=typer.colors.GREEN, err=True)
        raise typer.Exit(0)
    
    # The dispatcher's sole responsibility is to compile logical plans.
    # All other proposal types are passed through for the orchestrator to handle.
    if proposal.spf_plan_update:
        typer.echo("Logical plan proposal detected. Compiling...", err=True)
        compiler = SpfCompiler(project_root / 'plan')
        commands = compiler.compile_and_validate(proposal.spf_plan_update)
        
        proposal.commands = commands
        proposal.spf_plan_update = None  # Clear the logical plan part.
        
        if not proposal.summary:
            proposal.summary = "Apply compiled logical plan."
        if not proposal.event_type:
            proposal.event_type = "feat"
            
        typer.echo("Compilation successful. Proposal transformed to command list.", err=True)
    else:
        typer.echo("Standard proposal detected. Passing to orchestrator.", err=True)

    return proposal
