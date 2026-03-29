import typer
from pathlib import Path
from typing import Set

from mvs_harness.schemas.models import Proposal
from mvs_harness.sdf.utils import renumber_sdf_paths, parse_sdf_path

def renumber_sdf_directories_if_needed(proposal: Proposal, project_root: Path):
    """
    Analyzes a proposal for changes to SDF directories (plan/, spec/) and applies
    auto-renumbering to maintain a clean ordinal sequence.

    This is a standard, unconditional part of the SDF v3 workflow.
    """
    typer.echo("Checking for SDF directory changes to auto-renumber...", err=True)

    # 1. Identify all unique directories within plan/ and spec/ that were modified.
    modified_dirs: Set[Path] = set()
    if proposal.commands:
        for cmd in proposal.commands:
            if not cmd.path:
                continue
            path = Path(cmd.path)
            # Check if the path is within a designated SDF directory
            if path.parts and path.parts[0] in ('plan', 'spec'):
                # We care about the directory containing the modified item
                modified_dirs.add(path.parent)

    if not modified_dirs:
        typer.echo("  - No changes in SDF directories detected. Skipping renumbering.", err=True)
        return

    # 2. For each unique directory, calculate and apply renumbering.
    typer.echo(f"  - Found {len(modified_dirs)} modified SDF directories to process.", err=True)
    # FIX: Sort in reverse order to process deepest directories first. This prevents a
    # race condition where a parent directory is renamed before its children are processed.
    for dir_path_rel in sorted(list(modified_dirs), reverse=True):
        dir_path_abs = project_root / dir_path_rel
        if not dir_path_abs.is_dir():
            continue

        typer.echo(f"    - Processing: {dir_path_rel}", err=True)

        # Get a list of all items (files and dirs) in the directory that are valid SDF paths
        try:
            # THIS IS THE KEY CHANGE: Filter for only SDF v3 compliant paths before renumbering
            child_paths = [p for p in dir_path_abs.iterdir() if parse_sdf_path(p) is not None]
            
            if not child_paths:
                typer.echo("      - No SDF v3 compliant files/dirs found to renumber.", err=True)
                continue

            rename_operations = renumber_sdf_paths(child_paths)

            if not rename_operations:
                typer.echo(f"      - No renumbering needed.", err=True)
                continue

            typer.echo(f"      - Applying {len(rename_operations)} rename operation(s)...", err=True)
            for old_path, new_path in rename_operations:
                old_rel = old_path.relative_to(project_root)
                new_rel = new_path.relative_to(project_root)
                typer.echo(f"        - Renaming '{old_rel}' -> '{new_rel}'", err=True)
                old_path.rename(new_path)
        except Exception as e:
            typer.secho(f"      - ERROR: Failed to renumber contents of '{dir_path_rel}': {e}", fg=typer.colors.RED, err=True)
            # We continue to the next directory rather than failing the whole cycle.

    typer.echo("SDF auto-renumbering complete.", err=True)
