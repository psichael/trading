import os
import sys
import time
import asyncio
import signal
import pytz
import json
import argparse
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.core.master_controller_V2 import LiveGatedForge
from live.core.portfolio_manager import PortfolioManager
from live.data_code.cache_manager import DataCacheManager
from live.execution.broker_sim import SimBroker
from live.execution.broker_ibkr import IBKRBroker
from live.core.math_utils import get_friction

TIINGO_TOKEN = '1e1b9c4ef14bdc6ad07d14b6d5d8563c447ecbe3'
VIRTUAL_CAPITAL_USD = 3250.00
MAX_SLOTS = 1
ALLOCATION_PER_SLOT = VIRTUAL_CAPITAL_USD / MAX_SLOTS
ASSETS = [
    'NVDA', 'MSFT', 'AVGO', 'AAPL', 'AMZN', 'MSTR', 'COIN', 'PLTR', 'CRWD', 'TSLA', 
    'V', 'META', 'CAT', 'NEE', 'CBOE', 'NEM', 'PAAS', 'FCX', 'XOM', 'CCJ',
    'WMT', 'LLY', 'JPM', 'btcusd', 'ethusd', 'solusd', 'avaxusd', 'dogeusd', 'adausd', 'dotusd'
]

is_shutting_down = False

def handle_exit(sig, frame):
    global is_shutting_down
    is_shutting_down = True
    print('\n[SYSTEM] Shutdown signal received. Disconnecting...')
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

def is_equity_open(dt_naive):
    try:
        local_tz = datetime.now().astimezone().tzinfo
        aware_dt = dt_naive.replace(tzinfo=local_tz)
        est_dt = aware_dt.astimezone(pytz.timezone('US/Eastern'))
        if est_dt.weekday() > 4: return False
        if est_dt.hour < 9 or (est_dt.hour == 9 and est_dt.minute < 30): return False
        if est_dt.hour >= 16: return False
        return True
    except Exception:
        return True

async def connect_with_retry(broker, host='127.0.0.1', port=4002):
    for cid in range(1, 11):
        try:
            print(f'[IBKR] Attempting connection (ClientID: {cid})...')
            if hasattr(broker, 'ib') and broker.ib.isConnected():
                broker.ib.disconnect()
            
            await broker.connect(host, port, clientId=cid)
            print(f'✅ [IBKR] Connected successfully (ID: {cid})')
            return True
        except Exception as e:
            if 'already in use' in str(e) or '326' in str(e) or 'Timeout' in str(e):
                print(f'⚠️ [IBKR] ClientID {cid} is busy or timed out, rotating...')
                continue
            else:
                print(f'❌ [IBKR] Unexpected Connection Error: {e}')
                break
    return False

def log_telemetry(file_path, timestamp, ticker, price, signal, forge):
    state = forge.state
    with open(file_path, 'a') as f:
        f.write(f"{timestamp},{ticker},{price},{signal},{state.get('H1_Flux',0)},{state.get('M5_Flux',0)},{state.get('M5_Rds',0)}\n")

async def run_unified_engine(config_data=None):
    global ASSETS, VIRTUAL_CAPITAL_USD, MAX_SLOTS, ALLOCATION_PER_SLOT
    
    draft_size = 30
    lookback = 60
    max_sector_weight = 0.15
    hedge_quota = 0.20
    config_start_str = None
    
    if config_data:
        print(f'\n[SYSTEM] Injecting physics constraints from JSON matrix: {config_data.get("name", "Custom")}')
        if 'universe' in config_data:
            ASSETS = config_data['universe']
        
        params = config_data.get('parameters', {})
        if 'capital' in params: VIRTUAL_CAPITAL_USD = params['capital']
        if 'slots' in params: MAX_SLOTS = params['slots']
        if 'draft_size' in params: draft_size = params['draft_size']
        if 'lookback' in params: lookback = params['lookback']
        if 'max_sector_weight' in params: max_sector_weight = params['max_sector_weight']
        if 'hedge_quota' in params: hedge_quota = params['hedge_quota']
        if 'start' in params: config_start_str = params['start']
        
        ALLOCATION_PER_SLOT = VIRTUAL_CAPITAL_USD / MAX_SLOTS

    print('\n=== INITIALIZING UNIFIED GATED FORGE ORCHESTRATOR ===')
    print(f'Universe Size:   {len(ASSETS)} Assets')
    print(f'Draft Size:      {draft_size} Assets')
    print(f'Max Sector Wgt:  {max_sector_weight}')
    print(f'Hedge Quota:     {hedge_quota}')
    print(f'Capital / Slots: ${VIRTUAL_CAPITAL_USD} / {MAX_SLOTS}')
    
    cache = DataCacheManager(ASSETS, TIINGO_TOKEN)
    
    portfolio = PortfolioManager(
        ASSETS, 
        MAX_SLOTS,
        lookback_days=lookback,
        draft_size=draft_size,
        max_sector_weight=max_sector_weight,
        hedge_quota=hedge_quota
    )
    forges = {ticker: LiveGatedForge(ticker) for ticker in ASSETS}
    
    telemetry_file = os.path.join(cache.data_dir, 'telemetry.csv')
    with open(telemetry_file, 'w') as f:
        f.write('timestamp,ticker,price,signal,h1_flux,m5_state,m5_rds\n')
    
    if config_start_str:
        start_dt = datetime.strptime(config_start_str, "%Y-%m-%d")
        active_days = max(0, (datetime.now() - start_dt).days)
        calculated_depth = int(lookback * 1.5) + active_days + 10
        warmup_end_time = start_dt
    else:
        calculated_depth = lookback + 40
        warmup_end_time = None

    m5_timeline = cache.sync_and_load_history(depth_days=calculated_depth)
    if not warmup_end_time:
        warmup_end_time = m5_timeline.index[0] + timedelta(days=lookback + 10)
        
    sim_broker = SimBroker(VIRTUAL_CAPITAL_USD, MAX_SLOTS)
    
    last_h1_hour = -1
    last_quarter_week = -1
    last_draft_week = -1
    last_print_day = -1
    
    sim_entry_prices = {} 
    
    print('\n[PHASE 1.5] Constructing Aligned H1 Map...')
    h1_map = {}
    for ticker in ASSETS:
        if ticker in m5_timeline.columns:
            t_series = m5_timeline[ticker].dropna()
            t_h1 = t_series.resample('1H', label='right', closed='right').last().dropna()
            h1_map[ticker] = t_h1.reset_index().rename(columns={'index': 'time', ticker: 'close'})
            
    h1_ptrs = {t: 0 for t in ASSETS}
    
    print('\n[PHASE 1/2] Simulating + Hydrating Telemetry...')
    
    for current_time, row in m5_timeline.iterrows():
        current_week = current_time.isocalendar()[1]
        
        if current_time.day != last_print_day:
            last_print_day = current_time.day
            if current_time <= warmup_end_time:
                print(f'  -> Warming Up: {current_time.strftime("%Y-%m-%d")}')
            else:
                current_pnl = sim_broker.get_estimated_portfolio_value(row)
                print(f'\n  -> Simulating: {current_time.strftime("%Y-%m-%d")} | Est. Portfolio: ${current_pnl:,.2f}')

        if not portfolio.golden_list or (current_week % 13 == 0 and current_week != last_quarter_week):
            portfolio.rebuild_golden_list(current_time, cache.daily_master)
            last_quarter_week = current_week
        if not portfolio.active_roster or current_week != last_draft_week:
            portfolio.rebuild_active_roster(current_time, cache.daily_master)
            last_draft_week = current_week

        for ticker in ASSETS:
            h1_df = h1_map.get(ticker)
            if h1_df is not None:
                while h1_ptrs[ticker] < len(h1_df) and h1_df.at[h1_ptrs[ticker], 'time'] <= current_time:
                    forges[ticker].ingest_h1(h1_df.at[h1_ptrs[ticker], 'close'])
                    h1_ptrs[ticker] += 1
                    
            price = row.get(ticker)
            if pd.notna(price) and price > 0:
                forges[ticker].ingest_m5(price)

        if current_time <= warmup_end_time: continue

        held_tickers = sim_broker.get_holdings()
        active_roster = portfolio.active_roster
        recently_overridden = set()

        for ticker in list(held_tickers):
            is_roster_drop = ticker not in active_roster
            sig = forges[ticker].get_signal()
            current_flux = forges[ticker].state.get('H1_Flux', 0)
            force_exit = False
            
            if is_roster_drop:
                force_exit = True
                reason = 'Roster Drop'
            elif sig == 'WAIT':
                force_exit = True
                reason = 'Signal WAIT'
            else:
                cands = [c for c in active_roster if forges[c].get_signal() == 'LONG' and c != ticker and c not in held_tickers]
                if cands:
                    best_alt = max(cands, key=lambda x: forges[x].state.get('H1_Flux', 0) * (1 - (get_friction(x) * 10)))
                    best_flux = forges[best_alt].state.get('H1_Flux', 0)
                    dynamic_hurdle = 1.5 + (get_friction(best_alt) * 100)
                    if best_flux > (current_flux * dynamic_hurdle):
                        force_exit = True
                        reason = '1.5x Override'
                        recently_overridden.add(ticker)

            if force_exit:
                price = row.get(ticker, 0)
                if sim_broker.execute(ticker, 'SELL', price):
                    held_tickers.remove(ticker)
                    entry_p = sim_entry_prices.get(ticker, price)
                    pnl_pct = ((price - entry_p) / entry_p * 100) if entry_p > 0 else 0.0
                    print(f'    [SIM SELL] {ticker:<5} | PnL: {pnl_pct:>+6.2f}% | Reason: {reason:<14} | Exit Flux: {forges[ticker].state.get("H1_Flux", 0):.2f}')

        if len(held_tickers) < MAX_SLOTS:
            cands = [t for t in active_roster if forges[t].get_signal() == 'LONG' and t not in held_tickers and t not in recently_overridden]
            if cands:
                best_asset = max(cands, key=lambda x: forges[x].state.get('H1_Flux', 0) * (1 - (get_friction(x) * 10)))
                price = row.get(best_asset)
                if pd.notna(price) and price > 0:
                    if sim_broker.execute(best_asset, 'BUY', price):
                        held_tickers.append(best_asset)
                        sim_entry_prices[best_asset] = price
                        state = forges[best_asset].state
                        print(f'    [SIM BUY]  {best_asset:<5} | Flux: {state.get("H1_Flux", 0):>5.2f}/{state.get("Ceiling", 0):<5.2f} | Rds: {state.get("M5_Rds", 0):.4f}')
                    
    sim_broker.print_results(m5_timeline.iloc[-1])
    
    print('\n[PHASE 3] Live Execution Armed.')
    live_broker = IBKRBroker(MAX_SLOTS, ALLOCATION_PER_SLOT)
    connected = await connect_with_retry(live_broker, host='127.0.0.1', port=4002)
    if not connected: return
        
    try:
        while not is_shutting_down:
            now = datetime.now()
            sleep_seconds = (300 - (now.minute % 5) * 60 - now.second) + 5
            print(f'\n[LIVE] Next Tick in {sleep_seconds}s...')
            await asyncio.sleep(max(sleep_seconds, 1))
            if is_shutting_down: break
            
            current_time = datetime.now()
            current_prices = cache.fetch_live_tick()
            market_open_now = is_equity_open(current_time)
            
            if not current_prices:
                print('⚠️ [WARN] Empty live fetch. Waiting for next cycle.')
                continue

            held_tickers = live_broker.get_holdings()
            active_roster = portfolio.active_roster
            recently_overridden = set()
            
            print(f'\n=== ⚡ LIVE TICK: {current_time.strftime("%H:%M:%S")} ===')
            print(f'📦 Holdings: {held_tickers if held_tickers else "NONE"} | 🎯 Roster: {active_roster}')

            # Strict Top of Hour check for exact H1 parity
            is_h1_close = (current_time.minute < 5) and (current_time.hour != last_h1_hour)
            if is_h1_close: last_h1_hour = current_time.hour
            
            for ticker, price in current_prices.items():
                if is_h1_close: forges[ticker].ingest_h1(price)
                forges[ticker].ingest_m5(price)
                    
                if ticker in portfolio.active_roster:
                    log_telemetry(telemetry_file, current_time, ticker, price, forges[ticker].get_signal(), forges[ticker])

            for ticker in list(held_tickers):
                is_crypto = 'usd' in ticker.lower()
                if market_open_now or is_crypto:
                    if ticker not in active_roster or portfolio.check_exit_condition(ticker, held_tickers, forges):
                        price = current_prices.get(ticker, 0)
                        if price > 0:
                            if ticker in active_roster and forges[ticker].get_signal() != 'WAIT':
                                recently_overridden.add(ticker)
                                
                            print(f'[LIVE] Exit condition met for {ticker}. Executing SELL.')
                            success = await live_broker.execute(ticker, 'SELL', price)
                            if success: held_tickers.remove(ticker)

            if len(held_tickers) < MAX_SLOTS:
                cands = [t for t in active_roster if forges[t].get_signal() == 'LONG' and t not in held_tickers and t not in recently_overridden]
                if cands:
                    best_asset = max(cands, key=lambda x: forges[x].state.get('H1_Flux', 0) * (1 - (get_friction(x) * 10)))
                    is_crypto = 'usd' in best_asset.lower()
                    if market_open_now or is_crypto:
                        price = current_prices.get(best_asset, 0)
                        if price > 0:
                            print(f'[LIVE] Entry condition met for {best_asset} (Best Candidate: LONG). Executing BUY.')
                            success = await live_broker.execute(best_asset, 'BUY', price)
                            if success: held_tickers.append(best_asset)

    except Exception as e: print(f'\n❌ [RUNTIME ERROR] {e}')
    finally:
        print('\n[SYSTEM] Tearing down IBKR connection...')
        if hasattr(live_broker, 'ib') and live_broker.ib.isConnected(): live_broker.ib.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Live Bot Orchestrator')
    parser.add_argument('--config', type=str, help='Path to JSON configuration file')
    args = parser.parse_args()
    
    config_matrix = None
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_matrix = json.load(f)
    
    if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try: asyncio.run(run_unified_engine(config_data=config_matrix))
    except KeyboardInterrupt: pass
