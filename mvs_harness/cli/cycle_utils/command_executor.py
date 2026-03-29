import typer
import shutil
import pyperclip
from pathlib import Path
from typing import List

from mvs_harness.schemas.models import Proposal, Command


def apply_commands(commands: List[Command], root_path: Path, verbose: bool):
    """Core logic to apply a list of file system commands to a given root directory."""
    for cmd in commands:
        target_path = root_path / cmd.path
        try:
            if cmd.command == "create_file":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                content_to_write = cmd.content if cmd.content is not None else ""
                target_path.write_text(content_to_write)
                if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path}", err=True)
                try:
                    pyperclip.copy(content_to_write)
                    if verbose: typer.echo(f"    - Content copied to clipboard.", err=True)
                except pyperclip.PyperclipException:
                    if verbose: typer.echo(f"    - (Warning) Clipboard not available. Skipping copy.", err=True)
            elif cmd.command == "update_file":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(cmd.content if cmd.content is not None else "")
                if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path}", err=True)
            elif cmd.command == "delete_file":
                target_path.unlink(missing_ok=True)
                if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path}", err=True)
            elif cmd.command == "move_file" or cmd.command == "move_directory":
                if cmd.new_path:
                    new_target_path = root_path / cmd.new_path
                    new_target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.rename(new_target_path)
                    if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path} -> {cmd.new_path}", err=True)
                else:
                    if verbose: typer.echo(f"Error: 'new_path' is required for '{cmd.command}' command.", err=True)
                    raise typer.Exit(code=1)
            elif cmd.command == "create_directory":
                target_path.mkdir(parents=True, exist_ok=True)
                if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path}", err=True)
            elif cmd.command == "delete_directory":
                shutil.rmtree(target_path)
                if verbose: typer.echo(f"  - {cmd.command.replace('_', ' ')}: {cmd.path}", err=True)
            else:
                if verbose: typer.echo(f"Error: Unknown command type '{cmd.command}'", err=True)
                raise typer.Exit(code=1)
        except Exception as e:
            if verbose: 
                typer.echo(f"Error executing command {cmd.command} on {cmd.path}: {e}", err=True)
                raise typer.Exit(code=1)
            else:
                raise e


def execute_proposal_commands(proposal: Proposal, project_root: Path):
    """Handles all file system operations from the commands list."""
    typer.echo("Executing file system commands...", err=True)
    if not proposal.commands:
        typer.echo("  - No file system commands to execute.", err=True)
        return
    apply_commands(proposal.commands, project_root, verbose=True)
