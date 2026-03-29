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

def run_global_portfolio():
    TAX = 0.0001
    
    m5_files = glob.glob('bot/data/*_M5_sync_AI.csv')
    tickers = [os.path.basename(f).replace('_M5_sync_AI.csv', '') for f in m5_files]
    
    print(f'\n=== ASSEMBLING {len(tickers)}-ASSET UNIFIED MANIFOLD (1 QUARTER) ===')
    print('Loading and syncing DataFrames (this will take a moment)...')
    
    forges = {t: LiveGatedForge(t) for t in tickers}
    dfs_m5, h1_lists = {}, {}
    
    for t in tickers:
        m5 = standardize_df(pd.read_csv(f'bot/data/{t}_M5_sync_AI.csv'))
        h1 = standardize_df(pd.read_csv(f'bot/data/{t}_H1_sync_AI.csv'))
        
        # Target the most recent 1-quarter window, plus warmup
        max_date = m5['time'].max()
        start_date = max_date - pd.DateOffset(months=3) - pd.DateOffset(days=40)
        
        m5 = m5[m5['time'] >= start_date]
        h1 = h1[h1['time'] >= start_date]
        
        dfs_m5[t] = m5.set_index('time')['close']
        h1_lists[t] = h1.sort_values('time').reset_index(drop=True)

    m5_master = pd.DataFrame(dfs_m5).sort_index()
    
    capital = 10000.0
    start_capital = capital
    current_position = None
    shares = 0.0
    
    h1_ptrs = {t: 0 for t in tickers}
    latest_prices = {t: None for t in tickers}
    
    trade_log = []
    current_trade = {}
    
    print(f'\n=== EXECUTING {len(tickers)}-ASSET ALPHA ROTATION ===')
    print(f'Simulating tick-by-tick routing with Ruthless Reallocation. Stand by...')
    
    eval_start_date = m5_master.index[0] + pd.DateOffset(days=40)

    for row in m5_master.itertuples():
        current_time = row.Index
        signals = {}
        
        for t in tickers:
            close_val = getattr(row, t)
            if not pd.isna(close_val):
                latest_prices[t] = close_val
                
                while h1_ptrs[t] < len(h1_lists[t]) and h1_lists[t].at[h1_ptrs[t], 'time'] <= current_time:
                    forges[t].ingest_h1(h1_lists[t].at[h1_ptrs[t], 'close'])
                    h1_ptrs[t] += 1
                    
                forges[t].ingest_m5(close_val)
                signals[t] = forges[t].get_signal()

        if current_time < eval_start_date:
            continue

        # 1. EXIT & RUTHLESS REALLOCATION LOGIC
        if current_position is not None:
            current_sig = signals.get(current_position, 'WAIT')
            current_flux = forges[current_position].state.get('H1_Flux', 0)
            
            force_exit = False
            exit_reason = ''
            
            if current_sig == 'WAIT':
                force_exit = True
                exit_reason = 'Fracture'
            else:
                # Check for a massively superior asset (1.5x the energy)
                candidates = [t for t, sig in signals.items() if sig == 'LONG' and t != current_position]
                if candidates:
                    best_alt = max(candidates, key=lambda t: forges[t].state.get('H1_Flux', 0))
                    best_alt_flux = forges[best_alt].state.get('H1_Flux', 0)
                    
                    if best_alt_flux > (current_flux * 1.5):
                        force_exit = True
                        exit_reason = f'Ruthless -> {best_alt}'

            if force_exit:
                exit_price = latest_prices[current_position]
                capital = shares * exit_price * (1 - TAX)
                
                current_trade['Exit Time'] = current_time
                current_trade['Exit Price'] = exit_price
                current_trade['Capital Out'] = capital
                current_trade['Net %'] = (capital / current_trade['Capital In']) - 1
                current_trade['Reason'] = exit_reason
                trade_log.append(current_trade)
                
                current_position = None
                current_trade = {}
                shares = 0.0

        # 2. ENTRY LOGIC
        if current_position is None:
            candidates = [t for t, sig in signals.items() if sig == 'LONG']
            if candidates:
                best_asset = max(candidates, key=lambda t: forges[t].state.get('H1_Flux', 0))
                entry_price = latest_prices[best_asset]
                shares = (capital * (1 - TAX)) / entry_price
                current_position = best_asset
                
                current_trade = {
                    'Asset': best_asset,
                    'Entry Time': current_time,
                    'Entry Price': entry_price,
                    'Capital In': capital * (1 - TAX),
                    'Flux': forges[best_asset].state.get('H1_Flux', 0)
                }

    if current_position is not None:
        exit_price = latest_prices[current_position]
        capital = shares * exit_price * (1 - TAX)
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
    
    print(f'\n=== FINAL 95-ASSET UNIFIED RESULTS (1 QUARTER) ===')
    print(f'Starting Capital: ${start_capital:,.2f}')
    print(f'Ending Capital:   ${capital:,.2f}')
    print(f'Unified PnL:      {forge_pnl:.2%}')
    print(f'Total Rotations:  {len(trade_log)}')

if __name__ == '__main__':
    run_global_portfolio()
