from pathlib import Path
from typer.testing import CliRunner
import json
import pytest

from mvs_harness.cli.main import app

runner = CliRunner()

# Helper to create a consistent test environment
def setup_test_environment(base_dir: Path):
    # Create a dummy work_order.json
    work_order_path = base_dir / "work_order.json"
    work_order_content = {
        "active_task": "plan/e001/t001.yaml",
        "task_content": "This is a test task.",
        "required_context_files": ["spec/implementer_protocol"]
    }
    work_order_path.write_text(json.dumps(work_order_content))

    # Create dummy SDF spec files for context gathering
    spec_dir = base_dir / "spec" / "implementer_protocol"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "_topic.manifest.yaml").write_text("id: test-implementer-topic\ntitle: Implementer Protocol")

    # Create build directory and compile artifact
    build_dir = base_dir / "build" / "spec"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "implementer_protocol.md").write_text("<!-- sdf-id: test-implementer-topic -->\n# Test Implementer Protocol\n")
    (build_dir / "agent_knowledge.md").write_text("## Core Knowledge\n")

    return work_order_path, spec_dir

@pytest.fixture
def project_root_dir(tmp_path: Path) -> Path:
    return tmp_path

def test_agent_prepare_prints_to_stdout_by_default(project_root_dir: Path):
    """Verify prompt is printed to stdout when no output file is specified."""
    work_order_path, _ = setup_test_environment(project_root_dir)

    result = runner.invoke(
        app, [
            "agent", "prepare",
            "--work-order", str(work_order_path),
            "--project-root", str(project_root_dir)
        ], catch_exceptions=False
    )

    assert result.exit_code == 0
    # FIX: Make assertion robust against whitespace changes
    stdout_no_space = ''.join(result.stdout.split())
    assert '"core_context":{}' in stdout_no_space
    assert "operational_protocol" in result.stdout
    assert "work_order" in result.stdout

def test_agent_prepare_writes_to_output_file(project_root_dir: Path):
    """Verify prompt is written to the specified output file."""
    work_order_path, _ = setup_test_environment(project_root_dir)
    output_file = project_root_dir / "prompt.json"

    result = runner.invoke(
        app, [
            "agent", "prepare",
            "--work-order", str(work_order_path),
            "--project-root", str(project_root_dir),
            "--output", str(output_file)
        ], catch_exceptions=False
    )

    assert result.exit_code == 0
    assert output_file.is_file()
    
    prompt_content = json.loads(output_file.read_text())
    assert "operational_protocol" in prompt_content
    assert "work_order" in prompt_content
    assert prompt_content["core_context"] == {}
