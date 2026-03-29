import typer
import subprocess
from pathlib import Path

from mvs_harness.schemas.models import Proposal

def commit_changes(proposal: Proposal, project_root: Path):
    """Manages git operations. All proposals result in a commit."""
    typer.echo("Staging and committing changes...", err=True)
    try:
        status_result = subprocess.run(["git", "status", "--porcelain"], check=True, cwd=str(project_root), capture_output=True, text=True)
        # Also check if the event log itself was the only change
        log_file = project_root / ".ddio/events.log"
        if not status_result.stdout.strip():
            # If there are no other changes, we still need to commit the event log
            subprocess.run(["git", "add", str(log_file.relative_to(project_root))], check=True, cwd=str(project_root))
        else:
            subprocess.run(["git", "add", "."], check=True, cwd=str(project_root))

        typer.echo("  - git add .", err=True)
        
        commit_message = f"{proposal.event_type}(harness): {proposal.summary}"
        if proposal.completed_task_path:
            commit_message += f" | task: {proposal.completed_task_path}"
            
        subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=str(project_root))
        typer.echo(f'  - git commit -m "{commit_message}"', err=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        typer.echo(f"Error during git operation: {e}", err=True)
        raise typer.Exit(code=1)
