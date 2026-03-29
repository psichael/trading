import json
from typer.testing import CliRunner

from mvs_harness.cli.main import app
from mvs_harness.cli.plan import VIRTUAL_PLANNER_TASK_PATH, VIRTUAL_PLANNER_TASK_CONTENT
from mvs_harness.schemas.models import WorkOrder

runner = CliRunner()

def test_plan_start_creates_work_order(tmp_path):
    """Verify `ddio plan start` creates a correctly formatted work_order.json."""
    output_file = tmp_path / "work_order.json"

    result = runner.invoke(app, [
        "plan", 
        "start", 
        "--project-root", 
        str(tmp_path), 
        "--output", 
        str(output_file)
    ])

    assert result.exit_code == 0
    # Check the combined output stream instead of stderr
    assert "Planner agent work order generated at" in result.output
    assert output_file.exists()

    # Verify the content of the work order
    with output_file.open("r") as f:
        data = json.load(f)
    
    work_order = WorkOrder.model_validate(data)

    assert work_order.active_task == VIRTUAL_PLANNER_TASK_PATH
    assert work_order.task_content == VIRTUAL_PLANNER_TASK_CONTENT.strip()
    assert 'mvs_harness/schemas/spf_proposal.schema.json' in work_order.required_context_files
