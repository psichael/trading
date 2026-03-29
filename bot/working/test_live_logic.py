import pandas as pd
import numpy as np
from bot.master_controller_v2 import LiveGatedForge

def standardize_df(df):
    for col in df.columns:
        if any(key in col.lower() for key in ['time', 'date', 'stamp']):
            df = df.copy()
            df['time'] = pd.to_datetime(df[col], utc=True)
            return df
    raise KeyError(f'No time-like column found in {df.columns}')

def run_live_simulation(ticker='NVDA'):
    TAX = 0.0001
    try:
        df_m5 = standardize_df(pd.read_csv(f'bot/data/{ticker}_M5_sync_AI.csv'))
        df_h1 = standardize_df(pd.read_csv(f'bot/data/{ticker}_H1_sync_AI.csv'))
        
        forge = LiveGatedForge(ticker)
        
        pnl, audit_log = [], []
        in_pos = False
        last_h1_time = None
        trades = 0
        
        print(f'Starting Live-Logic Verification for {ticker}...')
        
        for i in range(len(df_m5)):
            row_m5 = df_m5.iloc[i]
            current_time = row_m5['time']
            
            new_h1 = df_h1[(df_h1['time'] <= current_time)]
            if not new_h1.empty:
                latest_h1 = new_h1.iloc[-1]
                if last_h1_time != latest_h1['time']:
                    forge.ingest_h1(latest_h1['close'])
                    last_h1_time = latest_h1['time']
                
            forge.ingest_m5(row_m5['close'])
            signal = forge.get_signal()
            
            if signal == 'WAIT_WARMUP':
                continue
                
            if i % (max(1, len(df_m5)//15)) == 0:
                state = forge.state.copy()
                state['Time'] = current_time
                audit_log.append(state)
                
            r = 0
            if signal == 'LONG':
                r = row_m5['close'] / df_m5.iloc[i-1]['close'] - 1 if i > 0 else 0
                if not in_pos:
                    r -= TAX
                    in_pos = True
                    trades += 1
                pnl.append(r)
            else:
                if in_pos:
                    pnl.append(-TAX)
                    in_pos = False
                    trades += 1
                else:
                    pnl.append(0)

        print('\n=== LIVE STATE AUDIT LOG ===')
        if audit_log:
            cols = ['Time', 'H1_Flux', 'H1_Tilt', 'Ceiling', 'M5_Rds', 'Signal']
            audit_df = pd.DataFrame(audit_log)[cols]
            print(audit_df.to_string(index=False))

        total_pnl = np.sum(pnl)
        print(f'\n=== LIVE-LOGIC VERIFICATION RESULTS ===')
        print(f'Ticker: {ticker}')
        print(f'Simulated Live PnL: {total_pnl:.2%}')
        print(f'Total Trades: {trades} | Total Tax: {trades * TAX:.6f}')
        
        if total_pnl > 0.5:
            print('STATUS: SUCCESS - Production logic matches High-Alpha expectations.')
        else:
            print('STATUS: WARNING - PnL deviation detected.')
            
    except Exception as e:
        print(f'[ERROR] {e}')

if __name__ == '__main__':
    run_live_simulation()