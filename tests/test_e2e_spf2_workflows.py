import json
import yaml
import shutil
import subprocess
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

from mvs_harness.cli.main import app

runner = CliRunner(mix_stderr=False)

def init_git_repo(path: Path):
    """Initializes a Git repository in the given path."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    # Configure user for commits to work
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)

def test_e2e_strategic_planning_workflow(tmp_path: Path):
    """Simulates the full happy-path of creating a new plan from scratch."""
    # Arrange: Create a realistic project structure with a git repo
    init_git_repo(tmp_path)

    project_root_real = Path(__file__).parent.parent
    schemas_dir_real = project_root_real / "mvs_harness" / "schemas"
    schemas_dir_temp = tmp_path / "mvs_harness" / "schemas"
    shutil.copytree(schemas_dir_real, schemas_dir_temp)

    (tmp_path / "spec" / "planner_protocol").mkdir(parents=True)
    (tmp_path / "plan").mkdir()

    # 1. User runs `ddio plan start`
    work_order_path = tmp_path / "work_order.json"
    result_start = runner.invoke(app, [
        "plan", "start", 
        "--project-root", str(tmp_path),
        "--output", str(work_order_path)
    ])
    assert result_start.exit_code == 0, result_start.output
    assert work_order_path.exists()

    # 2. Simulate Planner Agent creating a fully compliant logical proposal
    logical_proposal = {
        "plan_analysis": "This is the plan.",
        "summary": "Create initial project plan",
        "event_type": "feat",
        "spf_plan_update": {
            "create": {
                "epics": [
                    {
                        "temp_id": "e-001",
                        "title": "Initial Setup Epic",
                        "insert_after_epic_id": "start",
                        "component_ids": ["c1"],
                        "abstract": "First epic."
                    }
                ],
                "tasks": [],
                "contracts": []
            }
        }
    }
    proposal_path = tmp_path / "temp_proposal.json"
    with proposal_path.open("w") as f:
        json.dump(logical_proposal, f)

    # 3. User runs `ddio cycle execute` to execute the logical proposal
    # We patch the command generator because we are only testing the dispatcher logic
    with patch('mvs_harness.spf_compiler.compiler.SpfCompiler.compile_and_validate', return_value=[]):
        result_execute = runner.invoke(app, [
            "cycle", "execute",
            "--project-root", str(tmp_path),
            "--proposal", str(proposal_path)
        ], catch_exceptions=False)
    
    assert result_execute.exit_code == 0, result_execute.output
    assert "Logical plan proposal detected." in result_execute.stderr


def test_e2e_triage_and_fix_workflow(tmp_path: Path):
    """Simulates an agent being blocked and triggering the triage workflow."""
    # Arrange
    init_git_repo(tmp_path)

    # Schemas are needed for validation
    project_root_real = Path(__file__).parent.parent
    schemas_dir_real = project_root_real / "mvs_harness" / "schemas"
    schemas_dir_temp = tmp_path / "mvs_harness" / "schemas"
    shutil.copytree(schemas_dir_real, schemas_dir_temp)

    initial_wo_content = {"active_task": "plan/e1/t1.doc.yaml", "task_content": "Initial task content"}
    wo_path = tmp_path / "work_order.json"
    with wo_path.open("w") as f:
        json.dump(initial_wo_content, f)
    
    triage_proposal = {
        "plan_analysis": "Can't proceed.", # Must be valid for schema check
        "summary": "Requesting plan fix",
        "event_type": "chore",
        "plan_update_request": {
            "problem_statement": "It's broken.",
            "suggested_fix": "Fix it."
        }
    }
    proposal_path = tmp_path / "temp_proposal.json"
    with proposal_path.open("w") as f:
        json.dump(triage_proposal, f)
        
    # Act: Run the command without mocking to test the full, integrated workflow.
    result = runner.invoke(app, [
        "cycle", "execute",
        "--project-root", str(tmp_path),
        "--proposal", str(proposal_path)
    ], catch_exceptions=False)
    
    # Assert
    assert result.exit_code == 0, result.output
    
    # 1. Assert on the expected log output from the handler, proving it was called.
    assert "Plan update request detected. Pausing current task..." in result.stderr
    
    # 2. Assert on the side-effects of the triage handler
    paused_wo_path = tmp_path / ".ddio" / "paused_work_order.json"
    assert paused_wo_path.exists(), "The original work order was not paused correctly."
    
    with paused_wo_path.open("r") as f:
        paused_data = json.load(f)
    assert paused_data["active_task"] == "plan/e1/t1.doc.yaml"
    assert paused_data["task_content"] == "Initial task content"
    
    assert wo_path.exists(), "A new work order for the planner was not created."
    with wo_path.open("r") as f:
        new_wo_data = json.load(f)
    assert new_wo_data["active_task"] == "internal://planner-agent@1.0.0/triage"
    assert "It's broken." in new_wo_data["task_content"]
