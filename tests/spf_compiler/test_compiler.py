import pytest
import yaml
import uuid
from pathlib import Path

from mvs_harness.spf_compiler.compiler import SpfCompiler
from mvs_harness.schemas.models import (
    SpfProposal, CreateTask, UpdateTask, UpdateItems, CreateItems,
    CreateComponent, CreateContract, CreateEpic
)

@pytest.fixture
def empty_plan_project(tmp_path: Path) -> Path:
    """Creates a temporary project with an empty plan directory."""
    project_root = tmp_path / "empty_plan_project"
    plan_dir = project_root / "plan"
    plan_dir.mkdir(parents=True)
    return project_root

@pytest.fixture
def initial_plan_for_dependency_test(tmp_path: Path) -> Path:
    """Creates a temporary project with a single valid epic and task."""
    project_root = tmp_path / "dependency_test_project"
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa_epic-a"
    epic_dir.mkdir(parents=True)

    # Epic Manifest
    epic_manifest_content = yaml.dump({
        "id": "epic-a-id",
        "title": "Epic A",
        "status": "in-progress",
        "type": "spf-epic-manifest",
        "component_ids": [],
        "abstract": "..."
    })
    (epic_dir / "_topic.manifest.yaml").write_text(epic_manifest_content)

    # Task A
    task_a_content = yaml.dump({
        "id": "task-a-id",
        "title": "Task A",
        "status": "pending",
        "type": "task",
        "content": "Initial task.",
        "component_ids": [],
        "inputs": [],
        "outputs": [{"id": "output-a", "type": "file", "artifact_path": "a.txt"}]
    })
    (epic_dir / "0000_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1_task-a.doc.yaml").write_text(task_a_content)
    
    return project_root

@pytest.fixture
def plan_for_reorder_test(tmp_path: Path) -> Path:
    """Creates a temporary project with one epic and three tasks (A, B, C)."""
    project_root = tmp_path / "reorder_test_project"
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_epic0000-0000-0000-0000-000000000000_epic-for-reordering"
    epic_dir.mkdir(parents=True)

    epic_manifest = yaml.dump({"id": "epic-reorder-id", "title": "Epic For Reordering", "status": "in-progress", "type": "spf-epic-manifest", "component_ids": [], "abstract": "..."})
    (epic_dir / "_topic.manifest.yaml").write_text(epic_manifest)

    task_a = yaml.dump({"id": "task-a-id", "title": "Task A", "status": "pending", "type": "task", "content": "First task.", "component_ids": [], "inputs": [], "outputs": []})
    (epic_dir / "0000_taskaaaa-aaaa-aaaa-aaaa-000000000001_task-a.doc.yaml").write_text(task_a)

    task_b = yaml.dump({"id": "task-b-id", "title": "Task B", "status": "pending", "type": "task", "content": "Second task.", "component_ids": [], "inputs": [], "outputs": []})
    (epic_dir / "0001_taskbbbb-bbbb-bbbb-bbbb-000000000002_task-b.doc.yaml").write_text(task_b)

    task_c = yaml.dump({"id": "task-c-id", "title": "Task C", "status": "pending", "type": "task", "content": "Third task.", "component_ids": [], "inputs": [], "outputs": []})
    (epic_dir / "0002_taskcccc-cccc-cccc-cccc-000000000003_task-c.doc.yaml").write_text(task_c)
    
    return project_root

@pytest.fixture
def plan_with_circular_dependency(tmp_path: Path) -> Path:
    """Creates a project with a plan containing a circular dependency (A->B, B->A)."""
    project_root = tmp_path / "circular_dependency_project"
    plan_dir = project_root / "plan"
    epic_dir = plan_dir / "0000_circular-epic-uuid_circular-epic"
    epic_dir.mkdir(parents=True)

    epic_manifest = yaml.dump({"id": "circular-epic-id", "title": "Circular Epic", "status": "in-progress", "type": "spf-epic-manifest", "component_ids": [], "abstract": "..."})
    (epic_dir / "_topic.manifest.yaml").write_text(epic_manifest)

    # Task A depends on Task B
    task_a = yaml.dump({
        "id": "task-a-id", "title": "Task A", "status": "pending", "type": "task", "content": "...",
        "component_ids": [], 
        "inputs": [{"id": "input-from-b", "source_task_id": "task-b-id"}], 
        "outputs": [{"id": "output-a", "type": "file", "artifact_path": "a.txt"}]
    })
    (epic_dir / "0000_taskaaaa-circular_task-a.doc.yaml").write_text(task_a)

    # Task B depends on Task A, creating the cycle
    task_b = yaml.dump({
        "id": "task-b-id", "title": "Task B", "status": "pending", "type": "task", "content": "...",
        "component_ids": [], 
        "inputs": [{"id": "output-a", "source_task_id": "task-a-id"}], 
        "outputs": [{"id": "input-from-b", "type": "file", "artifact_path": "b.txt"}]
    })
    (epic_dir / "0001_taskbbbb-circular_task-b.doc.yaml").write_text(task_b)
    
    return project_root

def test_compiler_handles_full_epic_creation_with_temp_ids(empty_plan_project: Path):
    """
    Tests that the compiler can process a single proposal that creates a component,
    contract, epic, and task from scratch using temp_ids for internal references.
    This is the key validation for the planner workflow fix.
    """
    plan_root = empty_plan_project / "plan"
    compiler = SpfCompiler(plan_root=plan_root)

    proposal = SpfProposal(
        create=CreateItems(
            components=[
                CreateComponent(
                    temp_id="comp-schemas",
                    title="Schemas Component",
                    parent_component_id="root",
                    abstract="Component for managing schemas."
                )
            ],
            contracts=[
                CreateContract(
                    temp_id="contract-modify-schema",
                    title="Modify Schema Contract",
                    parent_component_id="comp-schemas", # Ref to temp_id
                    version="1.0.0",
                    abstract="A contract for modifying schemas."
                )
            ],
            epics=[
                CreateEpic(
                    temp_id="epic-schema-work",
                    title="Schema Work Epic",
                    component_ids=["comp-schemas"], # Ref to temp_id
                    abstract="Epic for all schema-related work."
                )
            ],
            tasks=[
                CreateTask(
                    temp_id="task-create-schema",
                    title="Create the initial schema",
                    parent_epic_id="epic-schema-work", # Ref to temp_id
                    implements_contract_id="contract-modify-schema", # Ref to temp_id
                    component_ids=["comp-schemas"], # Ref to temp_id
                    content="Define the first schema."
                )
            ]
        )
    )

    try:
        commands = compiler.compile_and_validate(proposal)
    except ValueError as e:
        pytest.fail(f"Compiler failed to validate a valid, self-contained proposal: {e}")

    assert len(commands) == 3, "Expected commands for dir, epic manifest, and task document"
    
    dir_cmd = next((cmd for cmd in commands if cmd.command == "create_directory"), None)
    epic_manifest_cmd = next((cmd for cmd in commands if "_topic.manifest.yaml" in cmd.path), None)
    task_doc_cmd = next((cmd for cmd in commands if ".doc.yaml" in cmd.path), None)

    assert dir_cmd is not None
    assert epic_manifest_cmd is not None
    assert task_doc_cmd is not None

    # Verify that temp_ids were replaced with real UUIDs
    epic_content = yaml.safe_load(epic_manifest_cmd.content)
    task_content = yaml.safe_load(task_doc_cmd.content)

    # Check that component was resolved and propagated
    assert len(epic_content["component_ids"]) == 1
    new_comp_id = epic_content["component_ids"][0]
    assert isinstance(uuid.UUID(new_comp_id), uuid.UUID) # Is a valid UUID
    assert task_content["component_ids"] == [new_comp_id]

    # Check that contract was resolved
    new_contract_id = task_content["implements_contract_id"]
    assert isinstance(uuid.UUID(new_contract_id), uuid.UUID)


def test_compiler_rejects_proposal_with_broken_dependency(initial_plan_for_dependency_test: Path):
    """
    Tests that the SPF compiler rejects a proposal to create a task that
    depends on a non-existent source_task_id.
    """
    plan_root = initial_plan_for_dependency_test / "plan"
    compiler = SpfCompiler(plan_root=plan_root)

    # Proposal to create Task B, which depends on a non-existent task
    proposal = SpfProposal(
        create=dict(
            tasks=[
                CreateTask(
                    temp_id="temp-task-b",
                    title="Task B",
                    parent_epic_id="epic-a-id",
                    insert_after_task_id="task-a-id",
                    component_ids=[],
                    implements_contract_id="",
                    inputs=[
                        {
                            "id": "input-b",
                            "source_task_id": "non_existent_task" # This is the invalid reference
                        }
                    ],
                    outputs=[],
                    content="This task has a broken dependency."
                )
            ]
        )
    )

    # Assert that a ValueError is raised due to the validation failure
    with pytest.raises(ValueError) as excinfo:
        compiler.compile_and_validate(proposal)

    assert "Plan validation failed" in str(excinfo.value)
    assert "invalid dependency" in str(excinfo.value)
    assert "source_task_id 'non_existent_task' not found" in str(excinfo.value)

def test_compiler_rejects_proposal_with_mismatched_io(initial_plan_for_dependency_test: Path):
    """
    Tests that the SPF compiler rejects a proposal where a task tries to consume
    an input artifact that is not produced by the source task.
    """
    plan_root = initial_plan_for_dependency_test / "plan"
    compiler = SpfCompiler(plan_root=plan_root)

    # Task A produces 'output-a'. This proposal tries to consume 'output-b' from it.
    proposal = SpfProposal(
        create=dict(
            tasks=[
                CreateTask(
                    temp_id="temp-task-b",
                    title="Task B",
                    parent_epic_id="epic-a-id",
                    insert_after_task_id="task-a-id",
                    component_ids=[],
                    implements_contract_id="",
                    inputs=[
                        {
                            "id": "output-b", # Mismatched ID
                            "source_task_id": "task-a-id"
                        }
                    ],
                    outputs=[],
                    content="This task has a mismatched dependency."
                )
            ]
        )
    )

    # Assert that a ValueError is raised due to the validation failure
    with pytest.raises(ValueError) as excinfo:
        compiler.compile_and_validate(proposal)

    assert "Plan validation failed" in str(excinfo.value)
    assert "requests input 'output-b' which is not an output of source task 'task-a-id'" in str(excinfo.value)

def test_compiler_handles_update_reorder_and_create_in_one_proposal(plan_for_reorder_test: Path):
    """
    Tests that the compiler correctly generates commands for a complex proposal
    involving updates, reordering of existing tasks, and creation of new tasks.
    Final desired order: A -> C -> D -> B
    """
    plan_root = plan_for_reorder_test / "plan"
    compiler = SpfCompiler(plan_root=plan_root)

    # Proposal: Update B's title, move C after A, create D after C
    proposal = SpfProposal(
        update=UpdateItems(tasks=[
            UpdateTask(id="task-b-id", title="Task B (Updated)"),
            UpdateTask(id="task-c-id", insert_after_task_id="task-a-id")
        ]),
        create=CreateItems(tasks=[
            CreateTask(
                temp_id="temp-task-d",
                title="Task D",
                parent_epic_id="epic-reorder-id",
                insert_after_task_id="task-c-id",
                component_ids=[],
                implements_contract_id="",
                inputs=[], outputs=[], content="Fourth task (new)."
            )
        ])
    )

    commands = compiler.compile_and_validate(proposal)

    epic_path = "plan/0000_epic0000-0000-0000-0000-000000000000_epic-for-reordering"

    # Find the generated UUID for the new task D to build expected paths
    create_cmd = next((cmd for cmd in commands if cmd.command == "create_file" and ".doc.yaml" in cmd.path), None)
    assert create_cmd is not None
    new_task_d_filename = create_cmd.path.split('/')[-1]
    
    expected_commands = [
        # 1. Move C to be after A (index 0 -> 1)
        {
            "command": "move_file", 
            "path": f"{epic_path}/0002_taskcccc-cccc-cccc-cccc-000000000003_task-c.doc.yaml",
            "new_path": f"{epic_path}/0001_taskcccc-cccc-cccc-cccc-000000000003_task-c.doc.yaml"
        },
        # 2. Create D to be after C (index 1 -> 2)
        {
            "command": "create_file",
            "path": f"{epic_path}/{new_task_d_filename}",
        },
        # 3. Move B to be after D (index 2 -> 3)
        {
            "command": "move_file",
            "path": f"{epic_path}/0001_taskbbbb-bbbb-bbbb-bbbb-000000000002_task-b.doc.yaml",
            "new_path": f"{epic_path}/0003_taskbbbb-bbbb-bbbb-bbbb-000000000002_task-b.doc.yaml"
        },
        # 4. Update B's content at its new location
        {
            "command": "update_file",
            "path": f"{epic_path}/0003_taskbbbb-bbbb-bbbb-bbbb-000000000002_task-b.doc.yaml",
        }
    ]

    assert len(commands) == 4
    for i, cmd in enumerate(commands):
        expected_cmd = expected_commands[i]
        assert cmd.command == expected_cmd["command"]
        assert cmd.path == expected_cmd["path"]
        if "new_path" in expected_cmd:
            assert cmd.new_path == expected_cmd["new_path"]

    # Verify content of the updated file
    update_cmd = commands[3]
    updated_content = yaml.safe_load(update_cmd.content)
    assert updated_content['title'] == "Task B (Updated)"
    assert updated_content['id'] == "task-b-id" # Ensure ID is preserved

def test_compiler_resolves_circular_dependency_paradox(plan_with_circular_dependency: Path):
    """
    Tests that the compiler can resolve a plan that starts in an invalid state
    (e.g., circular dependency) if the proposal corrects the issue.
    This validates that validation happens on the *final* state, not the initial one.
    """
    plan_root = plan_with_circular_dependency / "plan"
    compiler = SpfCompiler(plan_root=plan_root)

    # This proposal corrects the circular dependency by removing Task A's dependency on Task B.
    proposal = SpfProposal(
        update=UpdateItems(tasks=[
            UpdateTask(id="task-a-id", inputs=[])
        ])
    )

    # This should succeed because the final state after the update is valid.
    try:
        commands = compiler.compile_and_validate(proposal)
    except ValueError as e:
        pytest.fail(f"Compiler incorrectly rejected a valid correcting proposal: {e}")

    assert len(commands) == 1
    update_cmd = commands[0]
    assert update_cmd.command == "update_file"
    assert update_cmd.path.endswith("0000_taskaaaa-circular_task-a.doc.yaml")

    # Verify that the generated command actually fixes the content
    updated_content = yaml.safe_load(update_cmd.content)
    assert updated_content['id'] == "task-a-id"
    assert updated_content['inputs'] == []
