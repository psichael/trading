import json
import typer
from pathlib import Path
from datetime import datetime, timezone

from mvs_harness.schemas.models import Proposal

def log_proposal_event(proposal: Proposal, project_root: Path):
    """Creates a structured event from a proposal and appends it to the events log."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "event_type": proposal.event_type,
        "summary": proposal.summary,
    }
    # Conditionally add the task_file if a task was completed.
    if proposal.completed_task_path:
        event["task_file"] = proposal.completed_task_path
    
    log_file = project_root / ".ddio/events.log"
    log_file.parent.mkdir(exist_ok=True)
    with log_file.open("a") as f:
        f.write(json.dumps(event) + "\n")
    typer.echo(f"Appended event to {log_file}", err=True)
