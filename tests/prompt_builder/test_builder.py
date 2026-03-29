from pathlib import Path
from mvs_harness.prompt_builder.builder import AgentPromptBuilder
from mvs_harness.schemas.models import WorkOrder, AgentPrompt, ContextFile

def test_agent_prompt_builder_assembly(mock_project: Path):
    # 1. Define the WorkOrder for the test
    # This path MUST exist in the mock_project fixture
    active_task_path = "plan/task.doc.yaml"
    work_order = WorkOrder(
        active_task=active_task_path,
        task_content="content: 'This is the task.'",
        required_context_files=["src/main.py"]
    )

    # 2. Instantiate and run the builder
    builder = AgentPromptBuilder(work_order=work_order, project_root=mock_project)
    prompt = builder.assemble()

    # 3. Validate the assembled prompt
    assert isinstance(prompt, AgentPrompt)

    # Check protocol
    assert "# Test Implementer Protocol" in prompt.operational_protocol

    # Check that core_context is now an empty dict, as ddio_framework.json is removed
    assert prompt.core_context == {}

    # Check work order details
    assert prompt.work_order.active_task == active_task_path

    # Check context files - should be 2 (1 required + 1 active task file)
    assert len(prompt.context_files) == 2
    file_paths = {f.path for f in prompt.context_files}
    assert "src/main.py" in file_paths
    assert active_task_path in file_paths
