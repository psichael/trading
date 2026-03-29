import typer
import shutil
import tempfile
from pathlib import Path

from mvs_harness.schemas.models import Proposal
from mvs_harness.sdf.io import read_sdf_from_fs
from mvs_harness.cli.cycle_utils import command_executor

def validate_sdf_changes(proposal: Proposal, project_root: Path):
    """
    Validates that proposed changes to SDF directories (plan/, spec/) will not
    result in an invalid structure. It does this by applying the changes to a
    temporary copy and running validation on it.
    """
    sdf_commands = [
        cmd for cmd in proposal.commands
        if cmd.path and Path(cmd.path).parts and Path(cmd.path).parts[0] in ('plan', 'spec')
    ]

    if not sdf_commands:
        typer.echo("No SDF-related changes detected. Skipping pre-execution validation.", err=True)
        return

    typer.echo("SDF-related changes detected. Performing pre-execution validation...", err=True)
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # 1. Recreate current state in temp directory
        sdf_dirs_to_copy = ['plan', 'spec']
        for sdf_dir_name in sdf_dirs_to_copy:
            source_dir = project_root / sdf_dir_name
            if source_dir.is_dir():
                shutil.copytree(source_dir, temp_dir / sdf_dir_name, dirs_exist_ok=True)
        
        # 2. Apply proposed changes to the temporary state
        try:
            typer.echo("  - Applying proposed changes to temporary state...", err=True)
            # Use a private helper from the executor for this internal validation step
            command_executor._apply_commands(sdf_commands, temp_dir, verbose=False)
        except Exception as e:
            typer.secho(f"Fatal error preparing temporary state for SDF validation: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        # 3. Validate the temporary state
        typer.echo("  - Validating temporary structure...", err=True)
        try:
            validated_topics_count = 0
            for sdf_root_name in sdf_dirs_to_copy:
                sdf_root_dir = temp_dir / sdf_root_name
                if not sdf_root_dir.is_dir():
                    continue

                # An SDF topic is defined by a directory containing a manifest.
                # We find all such directories and validate each one.
                for manifest_path in sorted(sdf_root_dir.rglob("_topic.manifest.yaml")):
                    topic_dir = manifest_path.parent
                    typer.echo(f"    - Validating topic: '{topic_dir.relative_to(temp_dir)}'", err=True)
                    _ = read_sdf_from_fs(topic_dir)
                    validated_topics_count += 1
            
            if validated_topics_count > 0:
                typer.secho(f"  - SDF pre-execution validation successful ({validated_topics_count} topics validated).", fg=typer.colors.GREEN, err=True)
            else:
                typer.echo("  - No SDF topics found in proposal to validate.", err=True)

        except (FileNotFoundError, ValueError) as e:
            typer.secho(f"\nSDF VALIDATION FAILED. PROPOSAL REJECTED.", fg=typer.colors.RED, bold=True, err=True)
            typer.secho(f"The proposed changes would result in an invalid SDF structure. Error: {e}", fg=typer.colors.RED, err=True)
            typer.secho("No changes have been applied to the filesystem.", fg=typer.colors.YELLOW, err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred during SDF validation: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
