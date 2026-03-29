import typer
from typing import Optional
from simulation.main_sim import run_simulation

app = typer.Typer()

@app.callback()
def callback():
    """
    Forge Simulation CLI: High-fidelity historical testing.
    """
    pass

@app.command("run")
def run_cmd(
    tickers: str = typer.Option("ALL", help="Comma-separated tickers, or 'ALL' for full universe"),
    capital: float = typer.Option(50000.0, "--capital", "-c"),
    slots: int = typer.Option(1, "--slots", "-s", help="1 for aggressive compounding, 5 for portfolio"),
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    debug: bool = typer.Option(True, "--debug/--no-debug", help="Enable verbose forensics")
):
    """Execute historical simulation."""
    if tickers.strip().upper() == "ALL":
        ticker_list = ["ALL"]
    else:
        ticker_list = []
        for t in tickers.split(","):
            sym = t.strip().upper()
            if sym in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']:
                ticker_list.append(f"{sym}USD")
            else:
                ticker_list.append(sym)
            
    run_simulation(
        tickers=ticker_list, 
        initial_capital=capital, 
        slots=slots, 
        start=start, 
        end=end,
        debug=debug
    )

if __name__ == "__main__":
    app()