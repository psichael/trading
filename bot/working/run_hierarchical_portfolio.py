import pandas as pd
import numpy as np
import os
import glob
from bot.master_controller_v2 import LiveGatedForge

def standardize_df(df):
    for col in df.columns:
        if any(key in col.lower() for key in ['time', 'date', 'stamp']):
            df = df.copy()
            df['time'] = pd.to_datetime(df[col], utc=True)
            return df
    raise KeyError(f'No time-like column found in {df.columns}')

def get_friction(ticker):
    ticker = ticker.upper()
    if ticker in ['BTCUSD', 'ETHUSD', 'BTCUSDT', 'ETHUSDT', 'BTC', 'ETH']:
        return 0.0015
    elif any(crypto in ticker for crypto in ['SOL', 'ADA', 'DOGE', 'XRP', 'AVAX', 'MATIC', 'LINK', 'BNB']):
        return 0.0025
    elif any(fx in ticker for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'GLD', 'SLV']):
        return 0.0002
    elif ticker in ['VXX', 'UVXY']:
        return 0.0005
    else:
        return 0.0002

def run_hierarchical_portfolio():
    # Identify assets that have all 3 required manifolds
    m5_files = glob.glob('bot/data/*_M5_sync_AI.csv')
    tickers = []
    for f in m5_files:
        t = os.path.basename(f).replace('_M5_sync_AI.csv', '')
        if os.path.exists(f'bot/data/{t}_H1_sync_AI.csv') and os.path.exists(f'bot/data/{t}_D1_sync_AI.csv'):
            tickers.append(t)
            
    print(f'\n=== ASSEMBLING {len(tickers)}-ASSET HIERARCHICAL MANIFOLD (1 QUARTER) ===')
    print('Loading D1 (Macro), H1 (Gate), and M5 (Execution) DataFrames...')
    
    forges = {t: LiveGatedForge(t) for t in tickers}
    dfs_m5, h1_lists, d1_flux_series = {}, {}, {}
    
    for t in tickers:
        m5 = standardize_df(pd.read_csv(f'bot/data/{t}_M5_sync_AI.csv'))
        h1 = standardize_df(pd.read_csv(f'bot/data/{t}_H1_sync_AI.csv'))
        d1 = standardize_df(pd.read_csv(f'bot/data/{t}_D1_sync_AI.csv'))
        
        max_date = m5['time'].max()
        start_date = max_date - pd.DateOffset(months=3) - pd.DateOffset(days=40)
        
        m5 = m5[m5['time'] >= start_date]
        h1 = h1[h1['time'] >= start_date]
        d1 = d1[d1['time'] >= start_date].copy()
        
        # Pre-calculate D1_Flux for Layer 1 Drafting
        d1['ret'] = d1['close'].pct_change()
        d1['v_d1'] = d1['ret'].rolling(24).std() * 100 * np.sqrt(252)
        d1['f_d'] = (d1['v_d1'] / 2.0) * 4.2525
        d1['f_d'] = d1['f_d'].fillna(0)
        
        dfs_m5[t] = m5.set_index('time')['close']
        h1_lists[t] = h1.sort_values('time').reset_index(drop=True)
        d1_flux_series[t] = d1.sort_values('time').reset_index(drop=True)

    m5_master = pd.DataFrame(dfs_m5).sort_index()
    
    capital = 10000.0
    start_capital = capital
    current_position = None
    shares = 0.0
    
    h1_ptrs = {t: 0 for t in tickers}
    d1_ptrs = {t: 0 for t in tickers}
    latest_prices = {t: None for t in tickers}
    
    trade_log = []
    current_trade = {}
    
    active_roster = []
    last_draft_week = -1
    
    print(f'\n=== EXECUTING TWO-TIER ALPHA ROTATION ===')
    print('Running Weekly Macro Drafts -> Tick-by-Tick Micro Execution. Stand by...')
    
    eval_start_date = m5_master.index[0] + pd.DateOffset(days=40)

    for row in m5_master.itertuples():
        current_time = row.Index
        
        # === LAYER 1: THE MACRO DRAFT (Weekly) ===
        current_week = current_time.isocalendar()[1]
        if current_week != last_draft_week and current_time >= eval_start_date:
            last_draft_week = current_week
            
            scores = {}
            for t in tickers:
                while d1_ptrs[t] < len(d1_flux_series[t]) - 1 and d1_flux_series[t].at[d1_ptrs[t]+1, 'time'] <= current_time:
                    d1_ptrs[t] += 1
                
                raw_flux = d1_flux_series[t].at[d1_ptrs[t], 'f_d']
                fric = get_friction(t)
                
                # TCA Penalty: High fee assets lose up to 25% of their score
                score = raw_flux * (1 - (fric * 100))
                
                # Hysteresis Anchor: 15% defender bonus to prevent churn
                if t in active_roster:
                    score *= 1.15
                    
                scores[t] = score
                
            # Draft the Top 5
            sorted_tickers = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            active_roster = sorted_tickers[:5]

        # === LAYER 2: THE MICRO EXECUTION ===
        signals = {}
        for t in tickers:
            close_val = getattr(row, t)
            if not pd.isna(close_val):
                latest_prices[t] = close_val
                
                while h1_ptrs[t] < len(h1_lists[t]) and h1_lists[t].at[h1_ptrs[t], 'time'] <= current_time:
                    forges[t].ingest_h1(h1_lists[t].at[h1_ptrs[t], 'close'])
                    h1_ptrs[t] += 1
                    
                forges[t].ingest_m5(close_val)
                
                # Only ask for signals from the active roster or our current position
                if t in active_roster or t == current_position:
                    signals[t] = forges[t].get_signal()

        if current_time < eval_start_date:
            continue

        # 1. EXIT & TCA-AWARE RUTHLESS REALLOCATION
        if current_position is not None:
            current_sig = signals.get(current_position, 'WAIT')
            current_flux = forges[current_position].state.get('H1_Flux', 0)
            
            force_exit = False
            exit_reason = ''
            
            if current_sig == 'WAIT':
                force_exit = True
                exit_reason = 'Fracture'
            else:
                candidates = [t for t, sig in signals.items() if sig == 'LONG' and t != current_position and t in active_roster]
                if candidates:
                    best_alt = max(candidates, key=lambda t: forges[t].state.get('H1_Flux', 0) * (1 - (get_friction(t) * 10)))
                    best_alt_flux = forges[best_alt].state.get('H1_Flux', 0)
                    
                    dynamic_hurdle = 1.5 + (get_friction(best_alt) * 100)
                    
                    if best_alt_flux > (current_flux * dynamic_hurdle):
                        force_exit = True
                        exit_reason = f'TCA Jump -> {best_alt}'

            if force_exit:
                exit_price = latest_prices[current_position]
                fric = get_friction(current_position)
                capital = shares * exit_price * (1 - fric)
                
                current_trade['Exit Time'] = current_time
                current_trade['Exit Price'] = exit_price
                current_trade['Capital Out'] = capital
                current_trade['Net %'] = (capital / current_trade['Capital In']) - 1
                current_trade['Reason'] = exit_reason
                trade_log.append(current_trade)
                
                current_position = None
                current_trade = {}
                shares = 0.0

        # 2. ENTRY LOGIC (Strictly from Active Roster)
        if current_position is None:
            candidates = [t for t, sig in signals.items() if sig == 'LONG' and t in active_roster]
            if candidates:
                best_asset = max(candidates, key=lambda t: forges[t].state.get('H1_Flux', 0) * (1 - (get_friction(t) * 10)))
                entry_price = latest_prices[best_asset]
                fric = get_friction(best_asset)
                
                shares = (capital * (1 - fric)) / entry_price
                current_position = best_asset
                
                current_trade = {
                    'Asset': best_asset,
                    'Entry Time': current_time,
                    'Entry Price': entry_price,
                    'Capital In': capital * (1 - fric),
                    'Flux': forges[best_asset].state.get('H1_Flux', 0)
                }

    if current_position is not None:
        exit_price = latest_prices[current_position]
        fric = get_friction(current_position)
        capital = shares * exit_price * (1 - fric)
        current_trade['Exit Time'] = m5_master.index[-1]
        current_trade['Exit Price'] = exit_price
        current_trade['Capital Out'] = capital
        current_trade['Net %'] = (capital / current_trade['Capital In']) - 1
        current_trade['Reason'] = 'End of Sim'
        trade_log.append(current_trade)

    print(f'\n=== PORTFOLIO ROTATION LOG (Top 20 Trades) ===')
    trade_df = pd.DataFrame(trade_log)
    if not trade_df.empty:
        top_trades = trade_df.sort_values(by='Net %', ascending=False).head(20)
        top_trades['Net %'] = top_trades['Net %'].apply(lambda x: f'{x:.2%}')
        top_trades['Capital Out'] = top_trades['Capital Out'].apply(lambda x: f'${x:,.2f}')
        top_trades['Entry Time'] = top_trades['Entry Time'].dt.strftime('%m-%d %H:%M')
        top_trades['Exit Time'] = top_trades['Exit Time'].dt.strftime('%m-%d %H:%M')
        print(top_trades[['Asset', 'Entry Time', 'Exit Time', 'Reason', 'Capital Out', 'Net %']].to_string(index=False))

    forge_pnl = (capital / start_capital) - 1
    
    print(f'\n=== FINAL HIERARCHICAL RESULTS (1 QUARTER) ===')
    print(f'Starting Capital: ${start_capital:,.2f}')
    print(f'Ending Capital:   ${capital:,.2f}')
    print(f'Unified PnL:      {forge_pnl:.2%}')
    print(f'Total Rotations:  {len(trade_log)}')

if __name__ == '__main__':
    run_hierarchical_portfolio()
