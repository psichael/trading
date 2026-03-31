import sys
import os
import json
import typer
from datetime import datetime
from typing import Optional

# Ensure project root is in path so 'simulation' module can be resolved
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from simulation.main_sim_v2 import run_simulation

# Fallback to hardcoded token if import fails
try:
    from live.main_live_v2 import TIINGO_TOKEN
except ImportError:
    TIINGO_TOKEN = '1e1b9c4ef14bdc6ad07d14b6d5d8563c447ecbe3'

app = typer.Typer()

@app.callback()
def callback():
    """
    Forge Simulation CLI V2: Single Source of Truth Architecture.
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
    save: Optional[str] = typer.Option(None, "--save", help="Name to save this run's parameters as a JSON config"),
    tiingo: bool = typer.Option(False, "--tiingo", help="Use dynamic Tiingo data lake instead of local CSVs")
):
    """Execute historical simulation."""
    
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
                # Extended mapping to handle crypto pairs seamlessly for Tiingo
                if sym in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'DOGE', 'AVAX', 'XRP']:
                    universe.append(f"{sym.lower()}usd")
                else:
                    universe.append(sym)
            
    preloaded_data = None
    if tiingo:
        from shared.data_code.tiingo_adapter import TiingoSimAdapter
        
        depth_days = lookback + 40 
        if start:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                days_ago = (datetime.now() - start_dt).days
                depth_days = max(depth_days, days_ago + lookback + 10)
            except Exception as e:
                print(f"⚠️ [WARN] Could not parse start date for depth calculation: {e}")
        
        print(f"\n🌐 [SYSTEM] Initializing Tiingo Parity Test (Depth: {depth_days} days)...")
        
        active_universe = universe
        if universe == ["ALL"]:
            try:
                from live.main_live_v2 import ASSETS
                active_universe = ASSETS
            except ImportError:
                print("❌ [ERROR] Could not resolve 'ALL' for Tiingo. Ensure live.main_live_v2 is accessible.")
                return
                
        adapter = TiingoSimAdapter(active_universe, TIINGO_TOKEN)
        m5_timeline, h1_map, d1_map = adapter.get_simulation_data(depth_days=depth_days)
        preloaded_data = (m5_timeline, h1_map, d1_map)

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
        hedge_quota=hedge_quota,
        preloaded_data=preloaded_data
    )
    
    if save and results:
        config_dir = os.path.join(root_dir, "configs")
        os.makedirs(config_dir, exist_ok=True)
        
        filename = save if save.endswith('.json') else f"{save}.json"
        save_path = os.path.join(config_dir, filename)
        
        export_data = {
            "name": save,
            "reference_days": results["active_days"],
            "reference_pnl": round(results["roi"], 4),
            "execution_commands": {
                "simulation": f"python simulation/cli_v2.py run --config configs/{filename} --tiingo",
                "live": f"python live/main_live_v2.py --config configs/{filename}"
            },
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