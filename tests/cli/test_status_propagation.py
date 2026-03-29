import pytest
import yaml
from pathlib import Path

# The function under test was moved during refactoring.
from mvs_harness.cli.cycle_utils.governance import get_epic_propagation_proposal
from mvs_harness.schemas.models import Proposal, Command

@pytest.fixture
def project_structure(tmp_path: Path):
    """Creates a mock project plan structure for testing status propagation."""
    plan_dir = tmp_path / "plan"
    # Epic that should be completed
    epic_dir = plan_dir / "0000_my-epic"
    epic_dir.mkdir(parents=True)

    manifest = {"id": "my-epic", "title": "My Epic", "status": "pending"}
    (epic_dir / "_topic.manifest.yaml").write_text(yaml.dump(manifest))

    task1 = {"id": "task-1", "status": "completed", "content": "..."}
    (epic_dir / "0000_task-1.doc.yaml").write_text(yaml.dump(task1))

    task2 = {"id": "task-2", "status": "pending", "content": "..."} # This is the target task
    (epic_dir / "0001_task-2.doc.yaml").write_text(yaml.dump(task2))

    task3 = {"id": "task-3", "status": "finalized", "content": "..."}
    (epic_dir / "0002_task-3.doc.yaml").write_text(yaml.dump(task3))
    
    # A second epic that should NOT be completed
    epic2_dir = plan_dir / "0001_another-epic"
    epic2_dir.mkdir(parents=True)
    manifest2 = {"id": "another-epic", "title": "Another Epic", "status": "pending"}
    (epic2_dir / "_topic.manifest.yaml").write_text(yaml.dump(manifest2))

    task4 = {"id": "task-4", "status": "pending", "content": "..."}
    (epic2_dir / "0000_task-4.doc.yaml").write_text(yaml.dump(task4))

    task5 = {"id": "task-5", "status": "completed", "content": "..."}
    (epic2_dir / "0001_task-5.doc.yaml").write_text(yaml.dump(task5))

    return tmp_path

def test_propagation_when_all_tasks_complete(project_structure):
    """Verify a proposal is generated to set epic status to 'completed' when the last task is finished."""
    # Simulate the local file system change of the task being completed
    task_2_path = project_structure / "plan/0000_my-epic/0001_task-2.doc.yaml"
    task_2_data = yaml.safe_load(task_2_path.read_text())
    task_2_data['status'] = 'completed'
    task_2_path.write_text(yaml.dump(task_2_data))

    completed_task_relative_path = "plan/0000_my-epic/0001_task-2.doc.yaml"
    proposal = get_epic_propagation_proposal(completed_task_relative_path, project_structure)

    assert proposal is not None
    assert isinstance(proposal, Proposal)
    assert len(proposal.commands) == 1
    
    update_command = proposal.commands[0]
    assert update_command.command == "update_file"
    assert update_command.path == "plan/0000_my-epic/_topic.manifest.yaml"
    
    new_manifest_data = yaml.safe_load(update_command.content)
    assert new_manifest_data['status'] == 'completed'

def test_no_propagation_when_tasks_pending(project_structure):
    """Verify no proposal is generated if other tasks are still pending."""
    completed_task_relative_path = "plan/0001_another-epic/0001_task-5.doc.yaml"
    proposal = get_epic_propagation_proposal(completed_task_relative_path, project_structure)

    assert proposal is None

def test_no_propagation_when_no_task_path_is_provided(project_structure):
    """Verify the function returns None if no task path is given."""
    proposal = get_epic_propagation_proposal(None, project_structure)
    assert proposal is None

def test_idempotency_if_epic_already_completed(project_structure):
    """Verify no proposal is generated if the epic is already marked as completed."""
    manifest_path = project_structure / "plan/0000_my-epic/_topic.manifest.yaml"
    manifest_data = yaml.safe_load(manifest_path.read_text())
    manifest_data['status'] = 'completed'
    manifest_path.write_text(yaml.dump(manifest_data))

    completed_task_relative_path = "plan/0000_my-epic/0001_task-2.doc.yaml"
    proposal = get_epic_propagation_proposal(completed_task_relative_path, project_structure)

    assert proposal is None

def test_no_propagation_for_task_not_in_valid_epic(project_structure):
    """Verify no proposal is generated if the task's parent is not a valid epic."""
    (project_structure / "plan/orphan.doc.yaml").write_text("status: completed")
    
    # This should run without raising an exception and return None
    proposal = get_epic_propagation_proposal("plan/orphan.doc.yaml", project_structure)
    assert proposal is None
