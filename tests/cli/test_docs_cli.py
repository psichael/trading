import pytest
import yaml
from typer.testing import CliRunner
from pathlib import Path

from mvs_harness.cli import app
from mvs_harness.sdf.models import SdfTopicNode, TopicManifest, Doc
from mvs_harness.sdf.io import write_sdf_to_fs, read_sdf_from_fs

runner = CliRunner()

@pytest.fixture
def sample_sdf_tree_fs(tmp_path: Path) -> Path:
    """Provides a sample SDF structure on the filesystem and returns the root path."""
    sdf_tree = SdfTopicNode(
        manifest=TopicManifest(
            id="root-doc",
            title="Root Document",
            status="finalized",
            abstract="This is the main abstract.",
        ),
        sub_topics=[
            SdfTopicNode(
                manifest=TopicManifest(
                    id="section-1",
                    title="Section 1",
                    status="finalized",
                    abstract="Content for the first section.",
                ),
                docs=[
                    Doc(id="s1-para1", content="Details for 1.1")
                ]
            ),
            SdfTopicNode(
                manifest=TopicManifest(
                    id="section-2",
                    title="Section 2",
                    status="draft",
                    abstract="Content for the second section.",
                )
            ),
        ],
    )
    write_sdf_to_fs(sdf_tree, tmp_path)
    return tmp_path

# --- Tests for 'docs validate' ---

def test_cli_docs_validate_success(sample_sdf_tree_fs: Path):
    """Tests the 'docs validate' command on a valid structure."""
    result = runner.invoke(app, ["docs", "validate", str(sample_sdf_tree_fs)])
    assert result.exit_code == 0
    assert "Successfully validated 3 SDF topic(s)." in result.stdout
    assert "[SUCCESS] Validated topic: ." in result.stdout
    assert "[SUCCESS] Validated topic: ./0000_section-1" in result.stdout
    assert "[SUCCESS] Validated topic: ./0001_section-2" in result.stdout

def test_cli_docs_validate_fails_missing_manifest(tmp_path: Path):
    """Tests 'docs validate' fails when no topics are found."""
    result = runner.invoke(app, ["docs", "validate", str(tmp_path)])
    # No topics found is not a failure state for the validator itself, just a warning.
    assert result.exit_code == 0 
    assert "No SDF topics found" in result.stdout

def test_cli_docs_validate_fails_invalid_yaml(tmp_path: Path):
    """Tests 'docs validate' fails on invalid schema in the root topic."""
    # Create a valid manifest
    with (tmp_path / "_topic.manifest.yaml").open("w") as f:
        yaml.dump({"id": "test", "title": "Test", "status": "draft"}, f)
        
    invalid_doc = {"content": "some content"} # Missing 'id'
    with (tmp_path / "0000_bad-doc.doc.yaml").open("w") as f:
        yaml.dump(invalid_doc, f)
    
    result = runner.invoke(app, ["docs", "validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "Validation completed with errors." in result.stdout
    assert "[FAILURE] Validation failed for topic: ." in result.stdout
    assert "Schema validation failed" in result.stdout

def test_cli_docs_validate_partial_failure(sample_sdf_tree_fs: Path):
    """Tests recursive validation where one subtopic fails and another succeeds."""
    # Introduce an error in one sub-topic: create an invalid doc file in section-2 directory
    # Based on fixture logic (index 1, title "Section 2" -> dir "0001_section-2")
    section2_dir_name = "0001_section-2"
    
    # Create a malformed doc file in section-2. Missing 'id'.
    invalid_doc_path = sample_sdf_tree_fs / section2_dir_name / "invalid_doc.doc.yaml"
    with invalid_doc_path.open("w") as f:
        f.write("content: 'this doc has no id field'") # Malformed according to Doc schema

    result = runner.invoke(app, ["docs", "validate", str(sample_sdf_tree_fs)])

    # Verify overall failure
    assert result.exit_code == 1
    assert "Validation completed with errors." in result.stdout

    # Verify root topic success message
    assert "[SUCCESS] Validated topic: ." in result.stdout
    # Verify section 1 success message
    assert "[SUCCESS] Validated topic: ./0000_section-1" in result.stdout
    # Verify section 2 failure message
    assert f"[FAILURE] Validation failed for topic: ./{section2_dir_name}" in result.stdout
    assert "Schema validation failed" in result.stdout # The specific error message

# --- Tests for 'docs compile' ---

def test_cli_docs_compile_to_stdout(sample_sdf_tree_fs: Path):
    """Tests the 'docs compile' command printing to stdout."""
    result = runner.invoke(app, ["docs", "compile", str(sample_sdf_tree_fs)])
    assert result.exit_code == 0
    
    # Check for key parts of the compiled document
    assert "<!-- sdf-id: root-doc -->" in result.stdout
    assert "# Root Document" in result.stdout
    assert "This is the main abstract." in result.stdout
    assert "## Section 1" in result.stdout
    assert "Details for 1.1" in result.stdout
    assert "## Section 2" in result.stdout

def test_cli_docs_compile_to_file(sample_sdf_tree_fs: Path, tmp_path: Path):
    """Tests the 'docs compile' command writing to a file."""
    output_file = tmp_path / "output.md"
    result = runner.invoke(app, ["docs", "compile", str(sample_sdf_tree_fs), "--output", str(output_file)])

    assert result.exit_code == 0
    assert "Successfully compiled" in result.stdout
    assert output_file.is_file()

    content = output_file.read_text()
    assert "# Root Document" in content
    assert "Content for the second section." in content
    assert "<!-- sdf-id: section-1 -->" in content

# --- Tests for 'docs diff' ---

def test_cli_docs_diff(sample_sdf_tree_fs: Path, tmp_path: Path):
    """Tests the 'docs diff' command end-to-end."""
    before_dir = sample_sdf_tree_fs
    after_dir = tmp_path / "after"
    
    # 1. Read the 'before' tree
    tree = read_sdf_from_fs(before_dir)
    
    # 2. Introduce changes
    #    - Modify root abstract
    #    - Remove section-2
    #    - Add a new doc to section-1
    tree.manifest.abstract = "A new abstract."
    tree.sub_topics.pop(1) # Remove section-2
    tree.sub_topics[0].docs.append(Doc(id="s1-para-new", content="New content"))

    # 3. Write the 'after' tree to a new directory
    write_sdf_to_fs(tree, after_dir)

    result = runner.invoke(app, ["docs", "diff", str(before_dir), str(after_dir)])
    
    assert result.exit_code == 0
    
    # Check for expected output lines
    assert "[~] MODIFIED Topic Manifest: 'Root Document'" in result.stdout
    assert "- abstract changed" in result.stdout
    assert "[-] REMOVED Topic: 'Section 2'" in result.stdout
    assert "[+] ADDED Doc: 's1-para-new'" in result.stdout
