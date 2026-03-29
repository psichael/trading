import json
import yaml
from pathlib import Path

from tests.conftest import runner
from mvs_harness.cli.main import app

def test_e2e_valid_mid_list_task_insertion(spf_v2_project_with_two_tasks: Path):
    """
    Tests the full cycle of a Planner agent proposing a new task that is inserted
    between two existing tasks, verifying compilation and auto-renumbering.
    """
    # 1. Simulate Planner Agent creating a logical proposal to insert a task
    logical_proposal = {
        "plan_analysis": "Proposing a new task between two existing ones to test insertion logic.",
        "summary": "feat(plan): Insert new task mid-list",
        "event_type": "feat",
        "spf_plan_update": {
            "create": {
                "tasks": [
                    {
                        "temp_id": "t-new",
                        "title": "Inserted Task",
                        "parent_epic_id": "e001",
                        "insert_after_task_id": "t001", # CRITICAL: Insert after the first task
                        "component_ids": ["c1"],
                        "implements_contract_id": "none",
                        "inputs": [],
                        "outputs": [],
                        "content": "This task was inserted."
                    }
                ]
            }
        }
    }
    proposal_path = spf_v2_project_with_two_tasks / "proposal.json"
    proposal_path.write_text(json.dumps(logical_proposal))

    # 2. Execute the proposal via the CLI
    result = runner.invoke(app, [
        "cycle", "execute",
        "--project-root", str(spf_v2_project_with_two_tasks),
        "--proposal", str(proposal_path)
    ], catch_exceptions=False)

    # 3. Assert successful execution
    assert result.exit_code == 0, f"CLI command failed with output:\n{result.output}"
    assert "Logical plan proposal detected. Compiling..." in result.stderr
    assert "Compilation successful." in result.stderr

    # 4. Verify the final file system state
    epic_dir = spf_v2_project_with_two_tasks / "plan" / "0000_e001_test-epic"
    final_tasks = sorted(epic_dir.glob("*.doc.yaml"))

    assert len(final_tasks) == 3, "The new task file was not created or an extra file was created."

    # Check the final renumbered order
    assert final_tasks[0].name.startswith("0000_") and "first-task" in final_tasks[0].name
    assert final_tasks[1].name.startswith("0001_") and "inserted-task" in final_tasks[1].name
    assert final_tasks[2].name.startswith("0002_") and "second-task" in final_tasks[2].name

    # Verify content of the new file
    with final_tasks[1].open("r") as f:
        new_task_data = yaml.safe_load(f)
    assert new_task_data["title"] == "Inserted Task"
    assert new_task_data["id"] != "t-new" # The compiler should have assigned a real UUID
