import typer
from pathlib import Path

from .last import last_app
from .docs import docs_app
from .agent import agent_app
from .cycle import cycle_app, cycle_start, cycle_execute
from .agent import agent_prepare
from .plan import plan_app

app = typer.Typer(help="DDI-O MVS Harness CLI")

# Register sub-applications
app.add_typer(last_app, name="last")
app.add_typer(docs_app, name="docs")
app.add_typer(agent_app, name="agent")
app.add_typer(cycle_app, name="cycle")
app.add_typer(plan_app, name="plan")

# --- Top-level Shortcuts ---
@app.command("s", help="Shortcut for 'cycle start'.")
def shortcut_start(ctx: typer.Context):
    """Assembles the Orchestrator prompt to 'project_state.json'."""
    typer.echo("Running shortcut for 'cycle start'...", err=True)
    ctx.invoke(cycle_start, output_path=None, project_root=Path(".").resolve())

@app.command("p", help="Shortcut for 'agent prepare'.")
def shortcut_prepare(ctx: typer.Context):
    """Assembles the Agent prompt from 'work_order.json' to 'temp_agent_prompt.txt'."""
    typer.echo("Running shortcut for 'agent prepare'...", err=True)
    ctx.invoke(
        agent_prepare, 
        work_order_path=Path(".").resolve() / "work_order.json", 
        output_path=Path(".").resolve() / "temp_agent_prompt.txt",
        project_root=Path(".").resolve()
    )

@app.command("e", help="Shortcut for 'cycle execute'.")
def shortcut_execute(ctx: typer.Context):
    """Executes the proposal from 'temp_proposal.json'."""
    typer.echo("Running shortcut for 'cycle execute'...", err=True)
    ctx.invoke(cycle_execute, proposal_path=Path(".").resolve() / "temp_proposal.json", project_root=Path(".").resolve())


if __name__ == "__main__":
    app()
