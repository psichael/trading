import json
from pathlib import Path
from typing import Dict, Any
import typer

from mvs_harness.cli.cycle_logic import execute_proposal_logic
from mvs_harness.schemas.models import WorkOrder

# A new virtual task to provide context to the planner during a triage session.
TRIAGE_TASK_CONTENT_TEMPLATE = """
# Task: Resolve Blocked Agent (In-Flight Plan Refinement)

**URGENT:** An implementer agent has been blocked by a flaw in the project plan. Your task is to provide the smallest possible fix to unblock it.

**Original Agent's Problem Statement:**
---
{problem_statement}
---

**Original Agent's Suggested Fix:**
---
{suggested_fix}
---

**Action:**
- Propose a logical plan update that resolves the problem.
- Your goal is to make the minimal change required. Do not perform a full-scale replan unless absolutely necessary.
- The harness will resume the original agent after your fix is applied.
"""

def handle_proposal_execution(proposal_data: Dict[str, Any], project_root: Path):
    """
    Acts as the central dispatcher for all proposal executions.
    It either handles a triage request or forwards to the standard execution logic.
    """
    if "plan_update_request" in proposal_data:
        # --- Path A: Triage and Pause Workflow ---
        typer.secho("Plan update request detected. Pausing current task...", fg=typer.colors.YELLOW, err=True)
        request = proposal_data["plan_update_request"]

        # 1. Save the original work order
        original_wo_path = project_root / "work_order.json"
        if not original_wo_path.exists():
            typer.secho("Error: Cannot find original 'work_order.json' to pause.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        
        paused_dir = project_root / ".ddio"
        paused_dir.mkdir(exist_ok=True)
        paused_wo_path = paused_dir / "paused_work_order.json"
        original_wo_path.rename(paused_wo_path)
        typer.echo(f"  - Paused work order saved to: {paused_wo_path}", err=True)

        # 2. Create a new work order for the Planner Agent
        planner_task_content = TRIAGE_TASK_CONTENT_TEMPLATE.format(
            problem_statement=request['problem_statement'],
            suggested_fix=request['suggested_fix']
        ).strip()

        planner_work_order = WorkOrder(
            active_task="internal://planner-agent@1.0.0/triage",
            task_content=planner_task_content,
            required_context_files=[
                'mvs_harness/schemas/spf_proposal.schema.json',
                'spec/planner_protocol/',
                'plan/'
            ]
        )
        original_wo_path.write_text(planner_work_order.model_dump_json(indent=2))
        typer.echo(f"  - New planner work order created at: {original_wo_path}", err=True)

        # 3. Instruct the user
        typer.secho("\nNext Steps:", fg=typer.colors.CYAN, bold=True, err=True)
        typer.echo("1. Run 'ddio p' to prepare the Planner Agent's prompt.", err=True)
        typer.echo("2. Run the Planner Agent to get its logical proposal.", err=True)
        typer.echo("3. Run 'ddio e' with the Planner's proposal to fix the plan.", err=True)
        typer.echo("4. Once fixed, run 'ddio cycle resume' to continue the original task.", err=True)

    else:
        # --- Standard Execution Workflow ---
        # Pass the raw data to the main execution logic, which now handles dispatch.
        execute_proposal_logic(proposal_data, project_root)
