import os
import sys
import time
import asyncio
import signal
import pytz
import pandas as pd
from datetime import datetime, timedelta

# Ensure python can resolve the 'live' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.core.master_controller_V2 import LiveGatedForge
from live.core.portfolio_manager import PortfolioManager
from live.data_code.cache_manager import DataCacheManager
from live.execution.broker_sim import SimBroker
from live.execution.broker_ibkr import IBKRBroker

# === CONFIG ===
TIINGO_TOKEN = '1e1b9c4ef14bdc6ad07d14b6d5d8563c447ecbe3' 
VIRTUAL_CAPITAL_USD = 3250.00
MAX_SLOTS = 5
ALLOCATION_PER_SLOT = VIRTUAL_CAPITAL_USD / MAX_SLOTS
ASSETS = [
    'NVDA', 'MSFT', 'AVGO', 'AAPL', 'AMZN', 'MSTR', 'COIN', 'PLTR', 'CRWD', 'TSLA', 
    'V', 'META', 'CAT', 'NEE', 'CBOE', 'NEM', 'PAAS', 'FCX', 'XOM', 'CCJ',
    'WMT', 'LLY', 'JPM', 'btcusd', 'ethusd', 'solusd', 'avaxusd', 'dogeusd', 'adausd', 'dotusd'
]

# --- GLOBAL SHUTDOWN FLAG ---
is_shutting_down = False

def handle_exit(sig, frame):
    """Ensures IBKR connection is torn down cleanly on Ctrl+C."""
    global is_shutting_down
    is_shutting_down = True
    print("\n[SYSTEM] Shutdown signal received. Disconnecting...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

def is_equity_open(dt_naive):
    """Checks if a local naive datetime corresponds to active US Equity Market hours."""
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
            print(f"[IBKR] Attempting connection (ClientID: {cid})...")
            if hasattr(broker, 'ib') and broker.ib.isConnected():
                broker.ib.disconnect()
            
            await broker.connect(host, port, clientId=cid)
            print(f"✅ [IBKR] Connected successfully (ID: {cid})")
            return True
        except Exception as e:
            if "already in use" in str(e) or "326" in str(e) or "Timeout" in str(e):
                print(f"⚠️ [IBKR] ClientID {cid} is busy or timed out, rotating...")
                continue
            else:
                print(f"❌ [IBKR] Unexpected Connection Error: {e}")
                break
    return False

def log_telemetry(file_path, timestamp, ticker, price, signal, forge):
    state = forge.state
    with open(file_path, 'a') as f:
        f.write(f"{timestamp},{ticker},{price},{signal},{state.get('H1_Flux',0)},{state.get('M5_Flux',0)},{state.get('M5_Rds',0)}\n")

async def run_unified_engine():
    print("\n=== INITIALIZING UNIFIED GATED FORGE ORCHESTRATOR ===")
    
    cache = DataCacheManager(ASSETS, TIINGO_TOKEN)
    portfolio = PortfolioManager(ASSETS, MAX_SLOTS)
    forges = {ticker: LiveGatedForge(ticker) for ticker in ASSETS}
    
    telemetry_file = os.path.join(cache.data_dir, 'telemetry.csv')
    with open(telemetry_file, 'w') as f:
        f.write("timestamp,ticker,price,signal,h1_flux,m5_state,m5_rds\n")
    
    m5_timeline = cache.sync_and_load_history()
    sim_broker = SimBroker(VIRTUAL_CAPITAL_USD, MAX_SLOTS)
    warmup_end_time = m5_timeline.index[0] + timedelta(days=30) 
    
    last_h1_hour = -1
    last_quarter_week = -1
    last_draft_week = -1
    last_print_day = -1
    
    sim_entry_prices = {} 
    
    print(f"\n[PHASE 1/2] Simulating + Hydrating Telemetry...")
    
    for current_time, row in m5_timeline.iterrows():
        current_week = current_time.isocalendar()[1]
        market_open_now = is_equity_open(current_time)
        
        if current_time.day != last_print_day:
            last_print_day = current_time.day
            if current_time <= warmup_end_time:
                print(f"  -> Warming Up: {current_time.strftime('%Y-%m-%d')}")
            else:
                current_pnl = sim_broker.get_estimated_portfolio_value(row)
                print(f"\n  -> Simulating: {current_time.strftime('%Y-%m-%d')} | Est. Portfolio: ${current_pnl:,.2f}")

        if not portfolio.golden_list or (current_week % 13 == 0 and current_week != last_quarter_week):
            portfolio.rebuild_golden_list(current_time, cache.daily_master)
            last_quarter_week = current_week
        if not portfolio.active_roster or current_week != last_draft_week:
            portfolio.rebuild_active_roster(current_time, cache.daily_master)
            last_draft_week = current_week

        is_h1_close = current_time.hour != last_h1_hour
        if is_h1_close: last_h1_hour = current_time.hour
        
        for ticker in ASSETS:
            price = row[ticker]
            if not pd.isna(price):
                is_crypto = 'usd' in ticker.lower()
                
                # --- DATA INGESTION GUARD ---
                # Freeze physics for sleeping equities to prevent volatility decay
                if not is_crypto and not market_open_now:
                    pass
                else:
                    if is_h1_close: forges[ticker].ingest_h1(price)
                    forges[ticker].ingest_m5(price)

        if current_time <= warmup_end_time: continue

        held_tickers = sim_broker.get_holdings()
        active_roster = portfolio.active_roster
        
        for ticker in active_roster:
            if ticker in row and not pd.isna(row[ticker]):
                log_telemetry(telemetry_file, current_time, ticker, row[ticker], forges[ticker].get_signal(), forges[ticker])

        for ticker in list(held_tickers):
            is_roster_drop = ticker not in active_roster
            force_exit = False if is_roster_drop else portfolio.check_exit_condition(ticker, held_tickers, forges)
            
            if is_roster_drop or force_exit:
                price = row.get(ticker, 0)
                if await sim_broker.execute(ticker, 'SELL', price):
                    held_tickers.remove(ticker)
                    
                    if is_roster_drop:
                        reason = "Roster Drop"
                    elif forges[ticker].get_signal() == 'WAIT':
                        reason = "Signal WAIT"
                    else:
                        reason = "1.5x Override"
                        
                    entry_p = sim_entry_prices.get(ticker, price)
                    pnl_pct = ((price - entry_p) / entry_p * 100) if entry_p > 0 else 0.0
                    
                    state = forges[ticker].state
                    flux = state.get('H1_Flux', 0)
                    
                    print(f"    [SIM SELL] {ticker:<5} | PnL: {pnl_pct:>+6.2f}% | Reason: {reason:<14} | Exit Flux: {flux:.2f}")

        for ticker in active_roster:
            if ticker not in held_tickers and len(held_tickers) < MAX_SLOTS:
                if forges[ticker].get_signal() == 'LONG' and not pd.isna(row.get(ticker)):
                    price = row[ticker]
                    if await sim_broker.execute(ticker, 'BUY', price):
                        held_tickers.append(ticker)
                        sim_entry_prices[ticker] = price
                        
                        state = forges[ticker].state
                        flux = state.get('H1_Flux', 0)
                        ceil = state.get('Ceiling', 0)
                        rds = state.get('M5_Rds', 0)
                        tilt = state.get('H1_Tilt', 0)
                        
                        print(f"    [SIM BUY]  {ticker:<5} | Flux: {flux:>5.2f}/{ceil:<5.2f} | Rds: {rds:.4f} | Tilt: {tilt:.4f}")
                    
    sim_broker.print_results(m5_timeline.iloc[-1])
    
    print("\n[PHASE 3] Live Execution Armed.")
    
    live_broker = IBKRBroker(MAX_SLOTS, ALLOCATION_PER_SLOT)
    connected = await connect_with_retry(live_broker, host='127.0.0.1', port=4002)
    
    if not connected:
        print("❌ [FATAL] IBKR Connect Failed after 10 attempts. Exiting.")
        return
        
    try:
        while not is_shutting_down:
            now = datetime.now()
            sleep_seconds = (300 - (now.minute % 5) * 60 - now.second) + 15
            print(f"\n[LIVE] Next Tick in {sleep_seconds}s...")
            await asyncio.sleep(max(sleep_seconds, 5))
            
            if is_shutting_down: break
            
            current_time = datetime.now()
            current_prices = cache.fetch_live_tick()
            market_open_now = is_equity_open(current_time)
            
            if not current_prices:
                print("⚠️ [WARN] Empty live fetch. Waiting for next cycle.")
                continue

            held_tickers = live_broker.get_holdings()
            active_roster = portfolio.active_roster
            print(f"\n=== ⚡ LIVE TICK: {current_time.strftime('%H:%M:%S')} ===")
            print(f"📦 Holdings: {held_tickers if held_tickers else 'NONE'} | 🎯 Roster: {active_roster}")

            is_h1_close = current_time.hour != last_h1_hour
            if is_h1_close: last_h1_hour = current_time.hour
            
            for ticker, price in current_prices.items():
                is_crypto = 'usd' in ticker.lower()
                
                # --- DATA INGESTION GUARD ---
                # Freeze physics for sleeping equities to prevent volatility decay
                if not is_crypto and not market_open_now:
                    pass
                else:
                    if is_h1_close: forges[ticker].ingest_h1(price)
                    forges[ticker].ingest_m5(price)
                    
                if ticker in portfolio.active_roster:
                    log_telemetry(telemetry_file, current_time, ticker, price, forges[ticker].get_signal(), forges[ticker])

            current_week = current_time.isocalendar()[1]
            if current_week % 13 == 0 and current_week != last_quarter_week:
                print(f"\n[LIVE] Triggering Quarterly Golden List Rebuild...")
                portfolio.rebuild_golden_list(current_time, cache.daily_master)
                last_quarter_week = current_week
                
            if current_week != last_draft_week:
                print(f"\n[LIVE] Triggering Weekly Active Roster Draft...")
                portfolio.rebuild_active_roster(current_time, cache.daily_master)
                last_draft_week = current_week

            try:
                for ticker in list(held_tickers):
                    if ticker not in active_roster or portfolio.check_exit_condition(ticker, held_tickers, forges):
                        price = current_prices.get(ticker, 0)
                        if price > 0:
                            print(f"[LIVE] Exit condition met for {ticker}. Executing SELL.")
                            success = await live_broker.execute(ticker, 'SELL', price)
                            if success: held_tickers.remove(ticker)

                for ticker in active_roster:
                    if ticker not in held_tickers and len(held_tickers) < MAX_SLOTS:
                        signal = forges[ticker].get_signal()
                        price = current_prices.get(ticker, 0)
                        
                        if signal == 'LONG' and price > 0:
                            print(f"[LIVE] Entry condition met for {ticker} (LONG). Executing BUY.")
                            success = await live_broker.execute(ticker, 'BUY', price)
                            if success: held_tickers.append(ticker)
            except Exception as execution_error:
                print(f"❌ [LIVE EXECUTION ERROR] {execution_error}")

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\n❌ [RUNTIME ERROR] {e}")
    finally:
        print("\n[SYSTEM] Tearing down IBKR connection...")
        if hasattr(live_broker, 'ib') and live_broker.ib.isConnected():
            live_broker.ib.disconnect()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try: 
        asyncio.run(run_unified_engine())
    except KeyboardInterrupt: 
        pass
