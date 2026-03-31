import sys
import os
import typer
from typing import Optional

# Ensure project root is in path so 'simulation' module can be resolved
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

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
    lookback: int = typer.Option(30, "--lookback", "-l", help="Days to look back for the macro screener"),
    start: Optional[str] = typer.Option(None, "--start"),
    end: Optional[str] = typer.Option(None, "--end"),
    debug: bool = typer.Option(True, "--debug/--no-debug", help="Enable verbose forensics"),
    draft_size: int = typer.Option(30, "--draft-size", help="Number of top assets to select for the Golden List"),
    max_sector_weight: float = typer.Option(0.15, "--max-sector-weight", help="Maximum capital allocation per sector"),
    hedge_quota: float = typer.Option(0.2, "--hedge-quota", help="Percentage of capital reserved for hedging")
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
        lookback=lookback,
        start=start, 
        end=end,
        debug=debug,
        draft_size=draft_size,
        max_sector_weight=max_sector_weight,
        hedge_quota=hedge_quota
    )

if __name__ == "__main__":
    app()