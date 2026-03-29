import typer
import shutil
import tempfile
import os
from pathlib import Path

from mvs_harness.schemas.models import Proposal
from mvs_harness.sdf.io import read_sdf_from_fs
from mvs_harness.sdf.assembler import assemble_sdf_to_markdown
from mvs_harness.cli.cycle_utils import command_executor

def validate_sdf_changes(proposal: Proposal, project_root: Path):
    """
    Validates that proposed changes to SDF directories (plan/, spec/) will not
    result in an invalid structure. It does this by applying the changes to a
    temporary copy and running validation on it.
    """
    # If auto-renumbering is active, validation must be skipped because the
    # transient state (with decimal indexes) would be incorrectly flagged as invalid.
    if os.environ.get("MVS_SDF_AUTO_RENUMBER") == "true":
        typer.echo("SDF auto-renumbering is active. Skipping pre-execution validation.", err=True)
        return

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
            command_executor.apply_commands(sdf_commands, temp_dir, verbose=False)
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
            typer.secho("\nSDF VALIDATION FAILED. PROPOSAL REJECTED.", fg=typer.colors.RED, bold=True, err=True)
            typer.secho(f"The proposed changes would result in an invalid SDF structure. Error: {e}", fg=typer.colors.RED, err=True)
            typer.secho("No changes have been applied to the filesystem.", fg=typer.colors.YELLOW, err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.secho(f"An unexpected error occurred during SDF validation: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

def compile_sdf_specs(project_root: Path):
    """
    Recursively finds all SDF topics in the `spec/` directory, cleans the
    `build/spec` directory, and compiles each topic into a Markdown file.
    """
    typer.echo("Compiling SDF specifications to Markdown...", err=True)
    spec_dir = project_root / "spec"
    build_dir = project_root / "build" / "spec"

    if not spec_dir.is_dir():
        typer.echo("  - No 'spec' directory found. Skipping compilation.", err=True)
        return

    # Clean and recreate the build directory for specs
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"  - Cleaned and created {build_dir.relative_to(project_root)}", err=True)

    compiled_count = 0
    # Use rglob to find all manifest files, making the search recursive.
    for manifest_path in sorted(spec_dir.rglob("_topic.manifest.yaml")):
        topic_path = manifest_path.parent
        relative_topic_path = topic_path.relative_to(spec_dir)
        try:
            typer.echo(f"  - Compiling topic: {relative_topic_path}", err=True)
            root_node = read_sdf_from_fs(topic_path)
            markdown_content = assemble_sdf_to_markdown(root_node)
            
            # Create a unique output filename that preserves nesting to avoid collisions.
            output_filename_parts = list(relative_topic_path.parts)
            output_filename = f"{'__'.join(output_filename_parts)}.md"
            output_path = build_dir / output_filename
            
            output_path.write_text(markdown_content, encoding='utf-8')
            typer.echo(f"    -> Wrote {output_path.relative_to(project_root)}", err=True)
            compiled_count += 1
        except Exception as e:
            typer.echo(f"    -> Error compiling {relative_topic_path}: {e}", err=True)
            # Continue to next topic rather than failing the whole cycle
    
    if compiled_count == 0:
        typer.echo("  - No valid SDF topics found to compile.", err=True)
    else:
        typer.echo(f"SDF compilation complete. Compiled {compiled_count} topics.", err=True)
