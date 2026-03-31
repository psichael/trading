import sys
import os
import glob
import pandas as pd
from datetime import timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from simulation.core.master_controller_V2 import LiveGatedForge
from simulation.core.portfolio_manager import PortfolioManager
from simulation.execution.broker_sim import SimBroker
from simulation.data_code.data_processor import LocalDataIngestor
from simulation.core.math_utils import get_friction

def run_simulation(tickers, initial_capital, slots=1, lookback=30, start=None, end=None, debug=True, preloaded_data=None):
    data_dir = "data" if os.path.exists("data") else "bot/data"
    
    if preloaded_data:
        m5_timeline, h1_map, d1_map = preloaded_data
    else:
        if tickers == ["ALL"]:
            print(f"\n[DISCOVERY] Scanning '{data_dir}/' for complete asset universe...")
            m5_files = glob.glob(f"{data_dir}/*_M5_sync_AI.csv")
            valid_tickers = []
            for f in m5_files:
                t = os.path.basename(f).replace('_M5_sync_AI.csv', '')
                if os.path.exists(f"{data_dir}/{t}_H1_sync_AI.csv") and os.path.exists(f"{data_dir}/{t}_D1_sync_AI.csv"):
                    valid_tickers.append(t)
            tickers = sorted(valid_tickers)
            print(f"[DISCOVERY] Found {len(tickers)} valid assets with full Manifold data.")
            
            if not tickers:
                print("❌ No valid assets found in data directory.")
                return

        ingestor = LocalDataIngestor(data_dir=data_dir)
        m5_timeline, h1_map, d1_map = ingestor.load_aligned_data(tickers, start, end)
    
    if m5_timeline.empty:
        print("❌ No data found for the given criteria.")
        return

    broker = SimBroker(initial_capital, slots)
    portfolio = PortfolioManager(tickers, slots, lookback_days=lookback)
    forges = {t: LiveGatedForge(t) for t in tickers}

    h1_ptrs = {t: 0 for t in tickers}

    sim_start = m5_timeline.index[0]
    warmup_end = sim_start + timedelta(days=lookback + 10)
    
    print(f"\n=== SIMULATION ENGINE ARMED ===")
    print(f"Initial Capital: ${initial_capital:,.2f} | Slots: {slots}")
    print(f"Universe Size:   {len(tickers)} Assets")
    print(f"Lookback Window: {lookback} Days")
    print(f"Data Points:     {len(m5_timeline)} ticks")
    print(f"Start Date:      {sim_start}")
    print(f"Warmup Ends:     {warmup_end}")
    print(f"End Date:        {m5_timeline.index[-1]}\n")
    
    last_week = -1
    last_quarter = -1
    last_h1_hour = -1
    last_warmup_print = None

    for current_time, row in m5_timeline.iterrows():
        current_week = current_time.isocalendar()[1]
        is_warmup = current_time < warmup_end
        
        is_h1_close = current_time.hour != last_h1_hour
        if is_h1_close: 
            last_h1_hour = current_time.hour
            broker.record_equity(current_time, row)

        if not portfolio.golden_list or (current_week % 13 == 0 and current_week != last_quarter):
            portfolio.rebuild_golden_list(current_time, d1_map)
            last_quarter = current_week

        if not portfolio.active_roster or current_week != last_week:
            portfolio.rebuild_active_roster(current_time, d1_map)
            last_week = current_week

        for t in tickers:
            h1_df = h1_map.get(t)
            if h1_df is not None:
                while h1_ptrs[t] < len(h1_df) and h1_df.at[h1_ptrs[t], 'time'] <= current_time:
                    forges[t].ingest_h1(h1_df.at[h1_ptrs[t], 'close'])
                    h1_ptrs[t] += 1
            
            price = row.get(t)
            if pd.notna(price) and price > 0:
                forges[t].ingest_m5(price)

        if not is_warmup:
            held = broker.get_holdings()
            active = portfolio.active_roster

            for t in list(held):
                sig = forges[t].get_signal()
                current_flux = forges[t].state.get('H1_Flux', 0)
                force_exit = False
                
                if sig == 'WAIT':
                    force_exit = True
                else:
                    cands = [c for c in active if forges[c].get_signal() == 'LONG' and c != t]
                    if cands:
                        best_alt = max(cands, key=lambda x: forges[x].state.get('H1_Flux', 0) * (1 - (get_friction(x) * 10)))
                        best_flux = forges[best_alt].state.get('H1_Flux', 0)
                        dynamic_hurdle = 1.5 + (get_friction(best_alt) * 100)
                        if best_flux > (current_flux * dynamic_hurdle):
                            force_exit = True
                            
                if t not in active:
                    force_exit = True
                    
                if force_exit:
                    safe_price = row.get(t, 0.0) if not pd.isna(row.get(t)) else 0.0
                    if safe_price > 0:
                        broker.execute(t, 'SELL', safe_price)
            
            held = broker.get_holdings()
            if len(held) < slots:
                cands = [t for t in active if forges[t].get_signal() == 'LONG' and t not in held]
                if cands:
                    best_asset = max(cands, key=lambda x: forges[x].state.get('H1_Flux', 0) * (1 - (get_friction(x) * 10)))
                    price = row.get(best_asset)
                    if pd.notna(price) and price > 0:
                        broker.execute(best_asset, 'BUY', price)
                        
        else:
            if last_warmup_print != current_time.date():
                print(f"  [WARMUP] Ingesting history for {current_time.date()}...   ", end='\r')
                last_warmup_print = current_time.date()

    print("\n")
    broker.print_results(m5_timeline.iloc[-1])
    broker.generate_tearsheet(warmup_end=warmup_end)