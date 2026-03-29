import pytest
import json
import os
import subprocess
import uuid
import shutil
from pathlib import Path
from typer.testing import CliRunner

from mvs_harness.cli.main import app

runner = CliRunner()

@pytest.fixture
def sdf_v3_project(tmp_path: Path) -> Path:
    """Creates a project with a minimal SDF plan and an initialized git repo."""
    project_root = tmp_path / "sdf_v3_project"
    project_root.mkdir()

    # Initialize a git repository so commit commands don't fail
    subprocess.run(["git", "init"], cwd=str(project_root), check=True, capture_output=True)

    # Create dummy ddio files
    (project_root / ".ddio").mkdir()
    (project_root / ".ddio/events.log").touch()
    (project_root / "ddio_framework.json").write_text("{}")

    # Copy schemas required for validation by the dispatcher
    real_project_root = Path(__file__).parent.parent.parent
    schemas_dir_real = real_project_root / "mvs_harness" / "schemas"
    schemas_dir_temp = project_root / "mvs_harness" / "schemas"
    shutil.copytree(schemas_dir_real, schemas_dir_temp)

    # Create a valid SDF plan structure with one epic and one task
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_e001_test-epic"
    epic_dir.mkdir(parents=True, exist_ok=True)

    (epic_dir / "_topic.manifest.yaml").write_text(
        "id: e001\ntitle: 'Test Epic'\nstatus: active\nabstract: '...'"
    )

    (epic_dir / "0000_t001_initial-task.doc.yaml").write_text(
        "id: t001\ntitle: 'Initial Task'\nstatus: completed\ncontent: Initial task content"
    )

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=str(project_root), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(project_root), check=True)

    return project_root

def test_e2e_sdf_v3_insertion_and_renumbering(sdf_v3_project: Path):
    """
    Simulates an agent proposing an SDF v3 change, and verifies that the
    'cycle execute' command applies it and triggers auto-renumbering.
    """
    # 1. Define the agent's proposal to insert a new task
    new_task_uuid = str(uuid.uuid4())
    new_task_slug = "a-new-task-inserted"
    # CRITICAL: Use a decimal index for insertion
    # NOTE: The SDF v3 spec uses `[index]_[uuid]_[slug]`. The older plan parser uses `[prefix][index]_[slug]`.
    # The renumbering logic was updated to handle both. For this test, we use the full SDF v3 format.
    new_task_filename = f"0000.001_{new_task_uuid}_{new_task_slug}.doc.yaml"
    new_task_path = Path("plan/0000_e001_test-epic") / new_task_filename

    proposal_content = {
        "plan_analysis": "Inserting a new task to test SDF v3 workflow.",
        "summary": "feat(plan): Insert new SDF v3 task",
        "event_type": "feat",
        "commands": [
            {
                "command": "create_file",
                "path": str(new_task_path),
                "content": f"id: {new_task_uuid}\ntitle: A new task\nstatus: ready\ncontent: Test content"
            }
        ]
    }
    proposal_path = sdf_v3_project / "proposal.json"
    proposal_path.write_text(json.dumps(proposal_content))

    # 2. Set environment variables to enable SDF v3 features
    env = os.environ.copy()
    env["SDF_V3_ENABLED"] = "true"
    env["MVS_SDF_AUTO_RENUMBER"] = "true"

    # 3. Execute the command
    result = runner.invoke(
        app,
        [
            "cycle", "execute",
            "--proposal", str(proposal_path),
            "--project-root", str(sdf_v3_project)
        ],
        env=env,
        catch_exceptions=False
    )

    # 4. Assertions
    assert result.exit_code == 0, f"CLI command failed with stdout: {result.stdout}\nstderr: {result.stderr_bytes.decode() if result.stderr_bytes else 'N/A'}"

    # 5. Verify the final file system state after renumbering
    epic_dir = sdf_v3_project / "plan" / "0000_e001_test-epic"
    
    # The renumbering logic should only act on SDF v3 compliant paths.
    # The new file should be renumbered from 0000.001 -> 0000
    expected_new_filename = f"0000_{new_task_uuid}_{new_task_slug}.doc.yaml"
    
    assert (epic_dir / expected_new_filename).is_file(), f"{expected_new_filename} was not created"
    assert (epic_dir / "0000_t001_initial-task.doc.yaml").is_file(), "Original non-SDFv3 file should be untouched"
    assert len(list(epic_dir.glob('*.doc.yaml'))) == 2, "Incorrect number of task files"
