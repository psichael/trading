import typer
import json
from pathlib import Path

from mvs_harness.schemas.models import WorkOrder

plan_app = typer.Typer(help="Commands for interacting with the Planner Agent.")

VIRTUAL_PLANNER_TASK_PATH = "internal://planner-agent@1.0.0"
VIRTUAL_PLANNER_TASK_CONTENT = """
# Task: Define New Project Plan (SPFv2)

**Goal:** Your primary task is to collaborate with the user to define a new project plan using the Structured Planning Framework (SPF) v2.0.

**Analysis:**
1.  Review the `file_tree` and `recent_events` to understand the current state of the repository.
2.  Converse with the user to understand the high-level goals for the next phase of work.

**Action:**
- Your final output MUST be a single JSON object that validates against the main `mvs_harness/schemas/proposal.schema.json` schema.
- Your logical plan modifications MUST be placed within the `spf_plan_update` field of this proposal.
- You MUST NOT use the `commands` field.
- Use `temp_id` for creating new items and referencing them within the same proposal.
- The harness will compile your logical proposal into a valid SDF3 plan structure. You MUST NOT propose direct file system commands.
"""

@plan_app.command(
    "start",
    help="Generates a work order for the planner agent to create a new plan."
)
def plan_start(
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        "-p",
        help="The root directory of the MVS project.",
        resolve_path=True,
    ),
    output_path: Path = typer.Option(
        Path("work_order.json"),
        "--output",
        "-o",
        help="The output path for the generated work order.",
        resolve_path=True,
    )
):
    """
    Prepares a work order for the planner agent to initiate the Strategic Planning Lifecycle.
    """
    typer.secho("No active task found. Entering Planning Mode...", fg=typer.colors.GREEN, err=True)
    
    work_order = WorkOrder(
        active_task=VIRTUAL_PLANNER_TASK_PATH,
        task_content=VIRTUAL_PLANNER_TASK_CONTENT.strip(),
        required_context_files=[
            'mvs_harness/schemas/proposal.schema.json',
            'mvs_harness/schemas/spf_proposal.schema.json',
            'mvs_harness/schemas/definitions/',
            'spec/planner_protocol/'
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(work_order.model_dump_json(indent=2))

    typer.secho(
        f"Planner agent work order generated at: {output_path.relative_to(project_root.parent)}",
        fg=typer.colors.CYAN,
        err=True
    )
    typer.echo("Hint: Run 'ddio p' to prepare the full agent prompt from this work order.", err=True)