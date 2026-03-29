import json
import yaml
import shutil
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timezone

import pytest
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
def spf_v2_project_with_two_tasks(tmp_path: Path) -> Path:
    """Creates a project with an SPF plan containing one epic and two tasks."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Copy schemas required for validation by the dispatcher
    real_project_root = Path(__file__).parent.parent
    schemas_dir_real = real_project_root / "mvs_harness" / "schemas"
    schemas_dir_temp = project_root / "mvs_harness" / "schemas"
    shutil.copytree(schemas_dir_real, schemas_dir_temp)

    # Create a valid SDF plan structure with one epic and two tasks
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_e001_test-epic"
    epic_dir.mkdir(parents=True, exist_ok=True)

    epic_manifest = {
        "id": "e001", "title": "Test Epic", "status": "active",
        "type": "spf-epic-manifest", "component_ids": ["c1"], "abstract": "..."
    }
    (epic_dir / "_topic.manifest.yaml").write_text(yaml.dump(epic_manifest))

    task1_content = {
        "id": "t001", "title": "First Task", "status": "pending", "type": "task",
        "content": "First task content", "component_ids": ["c1"], "implements_contract_id": "none",
        "inputs": [], "outputs": []
    }
    task1_filename = f"0000_{uuid.uuid4()}_first-task.doc.yaml"
    (epic_dir / task1_filename).write_text(yaml.dump(task1_content))

    task2_content = {
        "id": "t002", "title": "Second Task", "status": "pending", "type": "task",
        "content": "Second task content", "component_ids": ["c1"], "implements_contract_id": "none",
        "inputs": [], "outputs": []
    }
    task2_filename = f"0001_{uuid.uuid4()}_second-task.doc.yaml"
    (epic_dir / task2_filename).write_text(yaml.dump(task2_content))

    # Initialize a git repository so commit commands don't fail
    init_git_repo(project_root)

    return project_root

@pytest.fixture
def mock_project(tmp_path: Path):
    """
    Creates a mock project structure, MANUALLY creating the final compiled
    SDF artifacts to ensure a stable test environment.
    """
    project_root = tmp_path
    
    # 1. Create ddio_framework.json
    framework_data = {"v": "3.10", "purpose": "Test Framework"}
    (project_root / "ddio_framework.json").write_text(json.dumps(framework_data))

    # 2. DEFINITIVE FIX: Manually create the separate, compiled protocol files.
    # This aligns the test fixture with the refactored SDF structure and loader logic.
    build_spec_dir = project_root / "build" / "spec"
    build_spec_dir.mkdir(parents=True, exist_ok=True)
    
    # Create implementer_protocol.md
    implementer_protocol_content = """<!-- sdf-id: test-implementer-protocol -->
# Test Implementer Protocol
"""
    (build_spec_dir / "implementer_protocol.md").write_text(implementer_protocol_content.strip())

    # Create orchestrator_protocol.md
    orchestrator_protocol_content = """<!-- sdf-id: test-orchestrator-protocol -->
# Test Orchestrator Protocol
"""
    (build_spec_dir / "orchestrator_protocol.md").write_text(orchestrator_protocol_content.strip())

    # 3. Create event log
    ddio_dir = project_root / ".ddio"
    ddio_dir.mkdir()
    event1 = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": "feat", "summary": "Initial commit", "task_file": "path/to/task1.yaml"}
    event2 = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": "fix", "summary": "Fix a bug", "task_file": "path/to/task2.yaml"}
    (ddio_dir / "events.log").write_text(json.dumps(event1) + "\n" + json.dumps(event2) + "\n")

    # 4. Create sample files for context loading
    src_dir = project_root / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')")
    
    utils_dir = src_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "helpers.py").write_text("# helper functions")

    # 5. Create both a legacy and a valid SPFv2 plan structure
    plan_dir = project_root / "plan"
    plan_dir.mkdir(exist_ok=True)

    # 5a. Create legacy file for tests that hardcode the old path
    (plan_dir / "task.doc.yaml").write_text("content: 'This is a legacy task.'")

    # 5b. Create a valid SPFv2 plan structure with a ready task for discovery tests
    epic_dir = plan_dir / "0001_test-epic"
    epic_dir.mkdir(parents=True, exist_ok=True)

    epic_manifest_content = yaml.dump({
        "id": "epic-test-id",
        "title": "Test Epic",
        "status": "in-progress",
        "type": "spf-epic-manifest"
    })
    (epic_dir / "_topic.manifest.yaml").write_text(epic_manifest_content)

    task_content = yaml.dump({
        "id": "task-test-id",
        "title": "A Ready Test Task",
        "status": "ready",
        "content": "This is the task.",
        "type": "task",
        "owner": "test-owner"
    })
    (epic_dir / "0001_a-ready-test-task.doc.yaml").write_text(task_content)

    return project_root
