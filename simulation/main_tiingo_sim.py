import os
import sys
from datetime import datetime

# Ensure resolution of simulation and live modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from simulation.main_sim import run_simulation
from simulation.data_code.tiingo_adapter import TiingoSimAdapter
# Reuse config from live bot for 100% parity
from live.main_live import ASSETS, TIINGO_TOKEN, VIRTUAL_CAPITAL_USD, MAX_SLOTS

def run_tiingo_parity_test():
    print("\n" + "="*60)
    print("🚀 STARTING TIINGO PARITY SIMULATION")
    print("Directly mirroring Live Bot data sourcing and physics...")
    print("="*60 + "\n")

    # 1. Initialize the Adapter
    adapter = TiingoSimAdapter(ASSETS, TIINGO_TOKEN)

    # 2. Fetch/Sync data
    m5_timeline, h1_map, d1_map = adapter.get_simulation_data()

    # 3. Run simulation with pre-loaded parity data
    run_simulation(
        tickers=ASSETS, 
        initial_capital=VIRTUAL_CAPITAL_USD, 
        slots=MAX_SLOTS, 
        preloaded_data=(m5_timeline, h1_map, d1_map)
    )

if __name__ == "__main__":
    run_tiingo_parity_test()