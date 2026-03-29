import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from mvs_harness.cli import triage_orchestrator
from mvs_harness.schemas.models import WorkOrder

@patch('mvs_harness.cli.triage_orchestrator.execute_proposal_logic')
def test_handle_standard_proposal(mock_execute_logic):
    """
    Verify a standard proposal is correctly forwarded to execute_proposal_logic.
    """
    # Arrange
    standard_proposal_data = {
        "summary": "A standard proposal",
        "plan_analysis": "...",
        "event_type": "feat",
        "commands": []
    }
    project_root = Path("/fake/project")

    # Act
    triage_orchestrator.handle_proposal_execution(standard_proposal_data, project_root)

    # Assert
    mock_execute_logic.assert_called_once_with(standard_proposal_data, project_root)


def test_handle_triage_proposal(tmp_path: Path):
    """
    Verify a triage proposal correctly pauses the old work order and creates a new one.
    """
    # Arrange
    original_wo_content = {
        "active_task": "original_task",
        "task_content": "Do the original thing.",
        "required_context_files": []
    }
    original_wo_path = tmp_path / "work_order.json"
    with original_wo_path.open("w") as f:
        json.dump(original_wo_content, f)

    triage_proposal_data = {
        "plan_update_request": {
            "problem_statement": "The database is missing.",
            "suggested_fix": "Create a migration task for the database."
        }
    }

    # Act
    triage_orchestrator.handle_proposal_execution(triage_proposal_data, tmp_path)

    # Assert
    paused_wo_path = tmp_path / ".ddio" / "paused_work_order.json"

    # 1. Original work order was moved to the paused location
    assert paused_wo_path.exists()
    with paused_wo_path.open("r") as f:
        paused_content = json.load(f)
    assert paused_content["active_task"] == "original_task"

    # 2. New work order for the planner was created in the original's place
    new_wo_path = tmp_path / "work_order.json"
    assert new_wo_path.exists()
    with new_wo_path.open("r") as f:
        new_wo_content = json.load(f)
    
    new_work_order = WorkOrder.model_validate(new_wo_content)
    assert new_work_order.active_task == "internal://planner-agent@1.0.0/triage"
    assert "The database is missing." in new_work_order.task_content
    assert "Create a migration task for the database." in new_work_order.task_content
    assert "plan/" in new_work_order.required_context_files
