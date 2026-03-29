import typer
import pyperclip
from pathlib import Path

from mvs_harness.schemas.models import OrchestratorPrompt, GoverningProtocol

def load_orchestrator_protocol(project_root: Path) -> GoverningProtocol:
    """Loads the orchestrator protocol content from its compiled SDF source."""
    # The protocol is defined as a top-level topic in SDF and compiled.
    # The new compiler creates one file per top-level topic.
    protocol_path = project_root / "build" / "spec" / "orchestrator_protocol.md"
    if not protocol_path.is_file():
        typer.echo(f"Error: Compiled orchestrator protocol not found at '{protocol_path}'", err=True)
        typer.echo("Hint: The 'orchestrator_protocol' topic should exist in 'spec/' and be compiled.", err=True)
        raise typer.Exit(code=1)
    protocol_content = protocol_path.read_text()

    source_file_str = str(protocol_path.relative_to(project_root))

    return GoverningProtocol(
        protocol_name="MVS Orchestrator Protocol",
        source_file=source_file_str,
        content=protocol_content
    )

def write_orchestrator_prompt_to_file(orchestrator_prompt: OrchestratorPrompt, output_path: Path):
    """Writes the assembled OrchestratorPrompt to the specified output path."""
    output_json = orchestrator_prompt.model_dump_json(indent=2)
    output_path.write_text(output_json)
    typer.echo(f"Orchestrator prompt written to {output_path}", err=True)
    try:
        pyperclip.copy(output_json)
        typer.echo(f"  - Prompt content copied to clipboard.", err=True)
    except pyperclip.PyperclipException:
        typer.echo(f"  - (Warning) Clipboard not available. Skipping copy.", err=True)
