import typer
import shutil
from pathlib import Path
from typing import Optional

from mvs_harness.last.models import ModuleNode
from mvs_harness.last.converter import py_to_last, last_to_py
from mvs_harness.last.io import write_last_to_fs, read_last_from_fs

last_app = typer.Typer(help="Commands for working with the Living AST (LAST).")

@last_app.command("disassemble", help="Converts a Python file into a LAST directory structure.")
def last_disassemble(
    source_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the source Python file."
    ),
    output_dir: Path = typer.Argument(
        ...,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        help="Path to the output directory for the LAST structure."
    )
):
    """Disassembles a Python file into LAST format."""
    typer.echo(f"Disassembling '{source_file}' into '{output_dir}'...")
    try:
        if output_dir.exists() and any(output_dir.iterdir()):
            typer.echo(f"Warning: Output directory '{output_dir}' is not empty. Clearing it.", err=True)
            shutil.rmtree(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
            
        source_code = source_file.read_text()
        last_tree = py_to_last(source_code)
        write_last_to_fs(last_tree, output_dir)
        typer.secho(f"Successfully disassembled to {output_dir}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error during disassembly: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@last_app.command("assemble", help="Reconstructs a Python file from a LAST directory structure.")
def last_assemble(
    source_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the source LAST directory."
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Path to save the output Python file. Prints to stdout if not provided."
    )
):
    """Assembles a Python file from LAST format."""
    typer.echo(f"Assembling from '{source_dir}'...")
    try:
        last_tree = read_last_from_fs(source_dir)
        # We expect a ModuleNode from the root of a valid structure
        if not isinstance(last_tree, ModuleNode):
             raise TypeError(f"Expected a ModuleNode at the root, but got {type(last_tree).__name__}")
        
        source_code = last_to_py(last_tree)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(source_code)
            typer.secho(f"Successfully assembled to {output_file}", fg=typer.colors.GREEN)
        else:
            print(source_code)

    except Exception as e:
        typer.secho(f"Error during assembly: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)