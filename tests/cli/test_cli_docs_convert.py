from pathlib import Path
from typer.testing import CliRunner

from mvs_harness.cli.docs import docs_app

runner = CliRunner()

# FIX: Added an H2 to correctly test subdirectory creation.
SAMPLE_MD_CONTENT = """# My Spec\n\nThis is the abstract.\n\n## First Section\n\nThis is a paragraph."""

def test_docs_convert_command_success():
    with runner.isolated_filesystem() as temp_dir:
        temp_dir_path = Path(temp_dir)
        input_file = temp_dir_path / "spec.md"
        input_file.write_text(SAMPLE_MD_CONTENT)
        output_dir = temp_dir_path / "output_sdf"

        result = runner.invoke(docs_app, ["convert", str(input_file), str(output_dir)])

        assert result.exit_code == 0
        assert "Successfully converted" in result.stdout

        assert output_dir.is_dir()
        assert (output_dir / "_topic.manifest.yaml").is_file()
        
        # Check for a directory that matches the new [index]_[uuid]_[slug] format
        sub_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        assert len(sub_dirs) == 1
        assert sub_dirs[0].name.startswith("0000_")
        assert sub_dirs[0].name.endswith("_first-section")

def test_docs_convert_command_input_not_found():
    result = runner.invoke(docs_app, ["convert", "nonexistent.md", "output_dir"])
    assert result.exit_code != 0
    assert "Invalid value" in result.stdout
    assert "does not exist" in result.stdout
