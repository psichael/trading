import sys
import os
import json
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
    hedge_quota: float = typer.Option(0.2, "--hedge-quota", help="Percentage of capital reserved for hedging"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to JSON config to load parameters from"),
    save: Optional[str] = typer.Option(None, "--save", help="Name to save this run's parameters as a JSON config")
):
    """Execute historical simulation."""
    
    # Override with config if provided
    universe = []
    if config and os.path.exists(config):
        print(f"[SYSTEM] Loading configuration from {config}")
        with open(config, 'r') as f:
            cfg_data = json.load(f)
            params = cfg_data.get("parameters", {})
            universe = cfg_data.get("universe", [])
            if "draft_size" in params: draft_size = params["draft_size"]
            if "max_sector_weight" in params: max_sector_weight = params["max_sector_weight"]
            if "hedge_quota" in params: hedge_quota = params["hedge_quota"]
            if "lookback" in params: lookback = params["lookback"]
            if "slots" in params: slots = params["slots"]
            if "capital" in params: capital = params["capital"]

    if not universe:
        if tickers.strip().upper() == "ALL":
            universe = ["ALL"]
        else:
            for t in tickers.split(","):
                sym = t.strip().upper()
                if sym in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']:
                    universe.append(f"{sym}USD")
                else:
                    universe.append(sym)
            
    results = run_simulation(
        tickers=universe, 
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
    
    if save and results:
        config_dir = os.path.join(root_dir, "configs")
        os.makedirs(config_dir, exist_ok=True)
        
        # Auto-append .json if missing
        filename = save if save.endswith('.json') else f"{save}.json"
        save_path = os.path.join(config_dir, filename)
        
        export_data = {
            "name": save,
            "reference_days": results["active_days"],
            "reference_pnl": round(results["roi"], 4),
            "parameters": {
                "draft_size": draft_size,
                "max_sector_weight": max_sector_weight,
                "hedge_quota": hedge_quota,
                "lookback": lookback,
                "slots": slots,
                "capital": capital
            },
            "universe": universe
        }
        
        with open(save_path, 'w') as f:
            json.dump(export_data, f, indent=4)
        print(f"\n💾 [SAVED] Configuration matrix safely written to {save_path}")

if __name__ == "__main__":
    app()