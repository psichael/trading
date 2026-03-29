import pytest
from pathlib import Path
from typer.testing import CliRunner

from mvs_harness.cli.main import app

runner = CliRunner(mix_stderr=False)

@pytest.fixture
def project_dir_no_ready_tasks(tmp_path: Path):
    """Creates a temporary project directory with a plan but no ready tasks."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    plan_dir = project_root / "plan"
    plan_dir.mkdir()

    # Create a dummy plan manifest required by the parser
    (plan_dir / "_plan.manifest.yaml").write_text(
        "id: test-plan\ntitle: Test Plan\nstatus: active\nowner: test"
    )

    # Create an epic with only a completed task
    epic_dir = plan_dir / "0001_epic"
    epic_dir.mkdir()
    (epic_dir / "_topic.manifest.yaml").write_text(
        "id: test-epic\ntitle: Test Epic\nstatus: active\nabstract: ..."
    )
    (epic_dir / "0001_task.doc.yaml").write_text(
        "id: t1\ntitle: T1\nstatus: completed\ncontent: '...'\ncomponent_ids: []"
    )
    
    # Create build/spec directory structure as cycle_start depends on it
    build_spec_dir = project_root / "build" / "spec"
    build_spec_dir.mkdir(parents=True, exist_ok=True)
    (build_spec_dir / "protocols__orchestrator-protocol.md").write_text("# Protocol")

    return project_root

def test_cycle_start_aborts_if_no_ready_tasks(project_dir_no_ready_tasks: Path):
    """
    If no ready tasks exist, `cycle start` should exit with an error and
    inform the user that planning is needed.
    """
    result = runner.invoke(
        app,
        ["cycle", "start", "--project-root", str(project_dir_no_ready_tasks)],
    )
    
    assert result.exit_code == 1, f"Expected exit code 1, but got {result.exit_code}. Stderr: {result.stderr}"
    assert "No active or pending tasks found" in result.stderr
    assert "Planning may be required" in result.stderr
    assert "Hint: Run 'ddio plan start'" in result.stderr
    assert not (project_dir_no_ready_tasks / "project_state.json").exists()
