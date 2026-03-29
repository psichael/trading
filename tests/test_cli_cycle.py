import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from mvs_harness.cli.main import app

runner = CliRunner(mix_stderr=False)

@pytest.fixture
def sdf_project_dir(tmp_path: Path) -> Path:
    """Creates a temp project dir with a valid SPF plan and the required SDF protocol specs."""
    (tmp_path / "ddio_framework.json").write_text('{}')

    # Create the source for the orchestrator protocol
    orchestrator_protocol_dir = tmp_path / "spec" / "orchestrator_protocol"
    orchestrator_protocol_dir.mkdir(parents=True, exist_ok=True)
    (orchestrator_protocol_dir / "_topic.manifest.yaml").write_text(
        "id: test-orchestrator-topic\ntitle: 'Orchestrator Protocol'\nstatus: finalized\n"
    )

    # Create the source for the agent protocol (needed for a complete test env)
    agent_protocol_dir = tmp_path / "spec" / "agent_protocol"
    agent_protocol_dir.mkdir(parents=True, exist_ok=True)
    (agent_protocol_dir / "_topic.manifest.yaml").write_text(
        "id: test-agent-topic\ntitle: 'Agent Protocol'\nstatus: finalized\n"
    )

    # Create a valid SPF plan structure
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "_plan.manifest.yaml").write_text(
        "id: test-plan\ntitle: 'Test Plan'\nstatus: active\nowner: 'tester'"
    )

    epic_dir = plan_dir / "0000_e1_active-epic"
    epic_dir.mkdir()
    (epic_dir / "_epic.manifest.yaml").write_text(
        "id: e1\ntitle: 'Active Epic'\nstatus: active\nabstract: '...'"
    )
    (epic_dir / "0000_t1_active_task.doc.yaml").write_text(
        "id: t1\ntitle: 'Active Task'\nstatus: pending\ncomponent_ids: []\ncontent: 'Active task content'\ntype: 'task'\nimplements_contract_id: 'none'"
    )
    return tmp_path


def test_cycle_start_finds_task_via_spf_discovery(sdf_project_dir: Path):
    """
    Tests that 'cycle start' finds the active task via SDF discovery when no
    .ddio/context_manifest.json exists.
    """
    result = runner.invoke(app, [
        "cycle", "start",
        "--output", str(sdf_project_dir / "state.json"),
        "--project-root", str(sdf_project_dir)
    ])

    assert result.exit_code == 0, f"CLI command failed with stderr: {result.stderr}"
    state = json.loads((sdf_project_dir / "state.json").read_text())

    expected_task_path = "plan/0000_e1_active-epic/0000_t1_active_task.doc.yaml"
    assert state['project_state']['active_task'] == expected_task_path
    assert state['project_state']['active_task_content'] == 'Active task content'


def test_cycle_start_aborts_when_no_ready_tasks_found(sdf_project_dir: Path):
    """
    Tests that 'cycle start' exits with an error if the plan is empty or has
    no ready tasks, instructing the user to run 'ddio plan'.
    """
    # Make the only task 'completed'
    task_path = sdf_project_dir / "plan/0000_e1_active-epic/0000_t1_active_task.doc.yaml"
    task_path.write_text(
        "id: t1\ntitle: 'Completed Task'\nstatus: completed\ncomponent_ids: []\ncontent: '...'\ntype: 'task'\nimplements_contract_id: 'none'"
    )

    result = runner.invoke(app, [
        "cycle", "start",
        "--output", str(sdf_project_dir / "state.json"),
        "--project-root", str(sdf_project_dir)
    ])
    
    # typer.Exit() without code defaults to 1
    assert result.exit_code == 1, "Expected non-zero exit code when no tasks are ready"
    assert "No active or pending tasks found" in result.stderr
    assert "ddio plan start" in result.stderr


def test_cycle_start_writes_to_specified_output_file(sdf_project_dir: Path):
    """Tests the --output flag directs the output correctly."""
    output_file = sdf_project_dir / "custom_name.json"
    result = runner.invoke(app, [
        "cycle", "start",
        "--output", str(output_file),
        "--project-root", str(sdf_project_dir)
    ])

    assert result.exit_code == 0, f"CLI command failed with stderr: {result.stderr}"
    assert output_file.exists()
    state = json.loads(output_file.read_text())
    expected_task_path = "plan/0000_e1_active-epic/0000_t1_active_task.doc.yaml"
    assert state['project_state']['active_task'] == expected_task_path
