import pytest
import json
import yaml
import shutil
import subprocess
from pathlib import Path
import jsonschema

from typer.testing import CliRunner

from mvs_harness.cli.main import app

runner = CliRunner(mix_stderr=False)

def init_git_repo(path: Path):
    """Initializes a Git repository in the given path."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True, capture_output=True)

@pytest.fixture
def e2e_project(tmp_path: Path) -> Path:
    """Creates a minimal project with schemas and a basic plan for E2E tests."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Copy schemas required for validation by the dispatcher
    real_project_root = Path(__file__).parent.parent.parent
    schemas_dir_real = real_project_root / "mvs_harness" / "schemas"
    schemas_dir_temp = project_root / "mvs_harness" / "schemas"
    shutil.copytree(schemas_dir_real, schemas_dir_temp)

    # Create a minimal plan with one epic so we have a valid parent_epic_id
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_e001_initial-epic"
    epic_dir.mkdir(parents=True, exist_ok=True)
    epic_manifest = {
        "id": "e001", "title": "Initial Epic", "status": "active",
        "type": "spf-epic-manifest", "component_ids": ["c1"], "abstract": "..."
    }
    (epic_dir / "_topic.manifest.yaml").write_text(yaml.dump(epic_manifest))

    # Initialize a git repository so commit commands don't fail
    init_git_repo(project_root)

    return project_root

def test_e2e_proposal_schema_violation(e2e_project: Path):
    """
    Tests that the harness rejects a logical proposal that violates the
    spf_proposal.schema.json.
    """
    # 1. Define a proposal that is missing the required 'title' field for a new task.
    invalid_logical_proposal = {
        "plan_analysis": "This proposal is deliberately invalid.",
        "summary": "feat(plan): Create a task without a title",
        "event_type": "feat",
        "spf_plan_update": {
            "create": {
                "tasks": [
                    {
                        "temp_id": "t-invalid",
                        # "title": "This is missing", # This is the violation
                        "parent_epic_id": "e001",
                        "insert_after_task_id": "start",
                        "component_ids": ["c1"],
                        "implements_contract_id": "none",
                        "inputs": [],
                        "outputs": [],
                        "content": "Invalid task content."
                    }
                ]
            }
        }
    }
    proposal_path = e2e_project / "proposal.json"
    proposal_path.write_text(json.dumps(invalid_logical_proposal))

    # 2. Execute the proposal via the CLI
    result = runner.invoke(app, [
        "cycle", "execute",
        "--project-root", str(e2e_project),
        "--proposal", str(proposal_path)
    ])

    # 3. Assert failure and check the error message
    assert result.exit_code != 0, "CLI command should have failed but it succeeded."
    assert "SCHEMA_ERROR: The proposal is invalid." in result.stderr
    assert "'title' is a required property" in result.stderr
