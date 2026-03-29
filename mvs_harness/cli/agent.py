import typer
import json
from pathlib import Path
from typing import Optional
import pyperclip

from pydantic import ValidationError

from mvs_harness.schemas.models import AgentPrompt, WorkOrder
from mvs_harness.prompt_builder.builder import AgentPromptBuilder
from mvs_harness.prompt_builder.loaders.context_files_loader import ContextFileNotFoundError
from mvs_harness.prompt_builder.loaders.protocol_loader import ProtocolNotFoundError


agent_app = typer.Typer(help="Commands for the Agent turn.")

@agent_app.command("prepare", help="Assembles the AgentPrompt JSON from a WorkOrder and local files.")
def agent_prepare(
    work_order_path: Path = typer.Option(
        ...,
        "--work-order", "-w",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the WorkOrder JSON file."
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Path to save the output JSON file. Prints to stdout if not provided."
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
        work_order_content = work_order_path.read_text(encoding='utf-8', errors='replace')
        work_order = WorkOrder.model_validate_json(work_order_content)
        
        # Use the new AgentPromptBuilder exclusively
        builder = AgentPromptBuilder(work_order=work_order, project_root=project_root)
        agent_prompt = builder.assemble()

        # Reorder the dictionary to place the protocol first for clarity
        prompt_dict = agent_prompt.model_dump()
        
        ordered_prompt_dict = {
            "operational_protocol": prompt_dict.pop("operational_protocol"),
            **prompt_dict
        }
        output_json = json.dumps(ordered_prompt_dict, indent=2)
        
        if output_path:
            output_path.write_text(output_json)
            typer.echo(f"Agent prompt written to {output_path}", err=True)
        else:
            print(output_json)

        # 1. Copy the generated AgentPrompt to the clipboard
        try:
            pyperclip.copy(output_json)
            typer.echo("Agent prompt content copied to clipboard.", err=True)
        except pyperclip.PyperclipException:
            typer.echo("(Warning) Clipboard not available. Skipping copy.", err=True)

        # 2. Clear the consumed input file (work_order.json)
        typer.echo(f"Clearing consumed work order file: {work_order_path}", err=True)
        work_order_path.write_text("")

        # 3. Clear the project_state.json from the previous (cycle start) step
        project_state_path = project_root / "project_state.json"
        if project_state_path.is_file():
            typer.echo(f"Clearing project_state.json from previous cycle: {project_state_path}", err=True)
            project_state_path.write_text("")

    except (
        ValidationError, 
        ContextFileNotFoundError, 
        ProtocolNotFoundError
    ) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}", err=True)
        raise typer.Exit(code=1)
