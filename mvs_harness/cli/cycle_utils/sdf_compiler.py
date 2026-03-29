import typer
import shutil
from pathlib import Path

from mvs_harness.sdf.io import read_sdf_from_fs
from mvs_harness.sdf.assembler import assemble_sdf_to_markdown

def compile_sdf_specs(project_root: Path):
    """
    Finds top-level SDF topics in the `spec/` directory, cleans the `build/spec`
    directory, and compiles each topic into a single, consolidated Markdown file.
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

    # Find only the top-level directories in spec/ that are valid SDF topics.
    top_level_topics = [
        d for d in spec_dir.iterdir() if d.is_dir() and (d / "_topic.manifest.yaml").exists()
    ]

    compiled_count = 0
    if not top_level_topics:
        typer.echo("  - No top-level SDF topics found in 'spec/'.", err=True)
        return

    for topic_path in sorted(top_level_topics):
        relative_topic_path = topic_path.relative_to(project_root)
        try:
            typer.echo(f"  - Compiling topic: {relative_topic_path}", err=True)
            root_node = read_sdf_from_fs(topic_path)
            markdown_content = assemble_sdf_to_markdown(root_node)
            
            # Create a clean output filename from the topic directory name.
            output_filename = f"{topic_path.name}.md"
            output_path = build_dir / output_filename
            
            output_path.write_text(markdown_content, encoding='utf-8')
            typer.echo(f"    -> Wrote {output_path.relative_to(project_root)}", err=True)
            compiled_count += 1
        except Exception as e:
            typer.echo(f"    -> Error compiling {relative_topic_path}: {e}", err=True)
            # Continue to next topic rather than failing the whole cycle
    
    if compiled_count > 0:
        typer.echo(f"SDF compilation complete. Compiled {compiled_count} top-level topic(s).", err=True)
