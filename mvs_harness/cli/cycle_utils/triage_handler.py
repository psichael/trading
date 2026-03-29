import json
from pathlib import Path

import typer

from mvs_harness.schemas.models import Proposal, WorkOrder

def handle_plan_update_request(proposal: Proposal, project_root: Path):
    """
    Handles a plan update request by pausing the current task and creating a new
    work order for the Planner Agent.
    """
    typer.secho("Plan update request detected. Pausing current task...", fg=typer.colors.YELLOW, err=True)

    ddio_dir = project_root / ".ddio"
    ddio_dir.mkdir(exist_ok=True)

    current_wo_path = project_root / "work_order.json"
    paused_wo_path = ddio_dir / "paused_work_order.json"

    # 1. Pause the current work order by moving it
    if current_wo_path.exists():
        current_wo_path.rename(paused_wo_path)
        typer.echo(f"Paused current work order to: {paused_wo_path}", err=True)
    else:
        typer.secho("Warning: No active work_order.json found to pause.", fg=typer.colors.YELLOW, err=True)

    # 2. Create a new work order for the Planner Agent
    if proposal.plan_update_request:
        planner_task_content = (
            f"**Problem Statement:**\n{proposal.plan_update_request.problem_statement}\n\n"
            f"**Suggested Fix:**\n{proposal.plan_update_request.suggested_fix}"
        )
        planner_work_order = WorkOrder(
            active_task="internal://planner-agent@1.0.0/triage",
            task_content=planner_task_content
        )
        current_wo_path.write_text(planner_work_order.model_dump_json(indent=2))
        typer.echo(f"Created new work order for Planner Agent at: {current_wo_path}", err=True)
