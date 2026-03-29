import typer
from pathlib import Path
from typing import Optional

from mvs_harness.cli.logic import docs_logic

docs_app = typer.Typer(help="Commands for working with the Structured Documentation Framework (SDF).")

@docs_app.command("convert", help="Converts a Markdown file into an SDF directory structure.")
def docs_convert(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the source Markdown file."
    ),
    output_dir: Path = typer.Argument(
        ...,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Path to the destination output directory."
    )
):
    """Converts a Markdown file into an SDF v3 directory structure."""
    typer.echo(f"Converting '{input_file.name}' to SDF structure in '{output_dir}'...")
    try:
        file_count = docs_logic.convert_markdown_to_sdf_structure(input_file, output_dir)
        typer.secho(f"\nSuccessfully converted and created {file_count} files in '{output_dir}'.", fg=typer.colors.GREEN, bold=True)
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during conversion: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@docs_app.command("validate", help="Validates the integrity of an SDF directory structure.")
def docs_validate(
    source_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the source SDF directory."
    )
):
    """Recursively validates all SDF topics found within the given directory."""
    typer.echo(f"Recursively validating SDF topics in '{source_dir}'...\n")
    has_errors = False
    
    try:
        results = docs_logic.validate_sdf_directory(source_dir)
    except Exception as e:
        typer.secho(f"[ERROR] An unexpected critical error occurred during validation: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not results:
        typer.secho(f"No SDF topics found in '{source_dir}'.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    for result in results:
        try:
            relative_topic_path = result.path.relative_to(source_dir)
        except ValueError:
            relative_topic_path = result.path

        display_path = f"./{relative_topic_path}" if relative_topic_path != Path('.') else "."

        if result.is_valid:
            typer.secho(f"[SUCCESS] Validated topic: {display_path}", fg=typer.colors.GREEN)
        else:
            has_errors = True
            typer.secho(f"[FAILURE] Validation failed for topic: {display_path}", fg=typer.colors.RED)
            error_lines = str(result.error).split('\n')
            for line in error_lines:
                typer.secho(f"  Error: {line}", fg=typer.colors.RED)

    typer.echo("\n" + "-" * 20)
    if has_errors:
        typer.secho(f"Validation completed with errors.", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)
    else:
        typer.secho(f"Successfully validated {len(results)} SDF topic(s).", fg=typer.colors.GREEN, bold=True)


@docs_app.command("diff", help="Compares two SDF directories and shows a semantic diff.")
def docs_diff(
    before_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the 'before' SDF directory."
    ),
    after_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the 'after' SDF directory."
    )
):
    """Compares two SDF directories and shows a semantic, UUID-based diff."""
    typer.echo(f"Comparing '{before_dir}' (before) with '{after_dir}' (after)...\n")
    try:
        output = docs_logic.diff_sdf_directories(before_dir, after_dir)
        typer.echo(output)
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"Error during diff: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during diff: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@docs_app.command("compile", help="Compiles an SDF directory into a single Markdown file.")
def docs_compile(
    source_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the source SDF directory."
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help="Path to save the output Markdown file. Prints to stdout if not provided."
    )
):
    """Compiles an SDF directory into a single Markdown file."""
    typer.echo(f"Compiling from '{source_dir}'...")
    try:
        markdown_content = docs_logic.compile_sdf_directory(source_dir)
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(markdown_content)
            typer.secho(f"Successfully compiled to {output_file}", fg=typer.colors.GREEN)
        else:
            print(markdown_content.strip())
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"Error during compilation: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during compilation: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
