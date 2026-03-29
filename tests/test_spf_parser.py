# tests/test_spf_parser.py
import pytest
from pathlib import Path
import yaml

from mvs_harness.spf_parser import load_plan, SPFValidationError
from mvs_harness.schemas.spf_legacy_models import PlanManifest, EpicManifest, TaskDocument

# --- Test Data ---

PLAN_MANIFEST_CONTENT = {
    "id": "test-plan",
    "title": "Test Plan",
    "status": "proposed",
    "owner": "test-owner",
    "components": [{"id": "comp-1", "type": "library", "abstract": "A component"}],
    "epics": [{"epic_id": "e01"}],
}

EPIC_MANIFEST_CONTENT = {
    "id": "e01",
    "title": "Test Epic",
    "status": "ready",
    "component_ids": ["comp-1"],
    "abstract": "An epic abstract",
}

TASK_DOC_CONTENT = {
    "id": "t01",
    "title": "Test Task",
    "status": "ready",
    "component_ids": ["comp-1"],
    "content": "Do the thing.",
}


# --- Fixtures ---

@pytest.fixture
def valid_plan_dir(tmp_path: Path) -> Path:
    """Creates a valid SPF directory structure for testing."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    # Plan Manifest
    with (plan_dir / "_plan.manifest.yaml").open("w") as f:
        yaml.dump(PLAN_MANIFEST_CONTENT, f)

    # Epic Directory
    epic_dir = plan_dir / "0001_e01_test-epic"
    epic_dir.mkdir()

    # Epic Manifest
    with (epic_dir / "_epic.manifest.yaml").open("w") as f:
        yaml.dump(EPIC_MANIFEST_CONTENT, f)

    # Task Document
    with (epic_dir / "0001_t01_test-task.doc.yaml").open("w") as f:
        yaml.dump(TASK_DOC_CONTENT, f)

    # Add an empty directory to ensure it's skipped
    (plan_dir / "empty_dir").mkdir()
    
    # Add a non-task yaml file to ensure it's skipped
    (epic_dir / "some_other.yaml").write_text("key: value")


    return plan_dir


# --- Test Cases ---

def test_load_plan_success(valid_plan_dir: Path):
    """Tests that a valid plan directory is parsed correctly."""
    plan = load_plan(valid_plan_dir)

    assert isinstance(plan.manifest, PlanManifest)
    assert plan.manifest.id == "test-plan"
    assert len(plan.epics) == 1

    epic = plan.epics[0]
    assert isinstance(epic.manifest, EpicManifest)
    assert epic.manifest.id == "e01"
    assert len(epic.tasks) == 1

    task = epic.tasks[0]
    assert isinstance(task.data, TaskDocument)
    assert task.data.id == "t01"
    assert task.path.name == "0001_t01_test-task.doc.yaml"


def test_load_plan_missing_plan_manifest_succeeds_with_default(tmp_path: Path):
    """Tests that a missing _plan.manifest.yaml results in a default plan."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    # This should not raise an error
    plan = load_plan(plan_dir)

    assert plan is not None
    assert plan.manifest.id == "default-plan"
    assert plan.manifest.title == "Default Plan"
    assert not plan.epics # An empty plan dir should have no epics


def test_load_plan_not_a_directory_raises_error(tmp_path: Path):
    """Tests that SPFValidationError is raised if the path is not a directory."""
    file_path = tmp_path / "not_a_dir"
    file_path.touch()
    with pytest.raises(SPFValidationError, match="Plan directory not found"):
        load_plan(file_path)


def test_load_plan_invalid_yaml_raises_error(valid_plan_dir: Path):
    """Tests that SPFValidationError is raised for malformed YAML."""
    # Corrupt the plan manifest
    (valid_plan_dir / "_plan.manifest.yaml").write_text("id: test\n  bad-indent")

    with pytest.raises(SPFValidationError, match="Failed to parse plan manifest"):
        load_plan(valid_plan_dir)


def test_load_plan_schema_validation_error_raises_error(valid_plan_dir: Path):
    """Tests that SPFValidationError is raised for content that fails schema validation."""
    # Remove a required field from the task document
    invalid_task_content = TASK_DOC_CONTENT.copy()
    del invalid_task_content["id"]
    
    task_path = valid_plan_dir / "0001_e01_test-epic" / "0001_t01_test-task.doc.yaml"
    with task_path.open("w") as f:
        yaml.dump(invalid_task_content, f)

    with pytest.raises(SPFValidationError, match="Failed to parse task document"):
        load_plan(valid_plan_dir)

def test_load_plan_skips_dirs_without_epic_manifest(valid_plan_dir: Path):
    """Tests that directories without an _epic.manifest.yaml are correctly skipped."""
    (valid_plan_dir / "no_manifest_dir").mkdir()
    (valid_plan_dir / "no_manifest_dir" / "task.doc.yaml").write_text("id: skip-me")

    plan = load_plan(valid_plan_dir)
    # Should only find the one valid epic
    assert len(plan.epics) == 1
    assert plan.epics[0].manifest.id == "e01"
