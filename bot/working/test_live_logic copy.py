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

def run_live_simulation(ticker):
    TAX = 0.0001
    try:
        df_m5 = standardize_df(pd.read_csv(f'bot/data/{ticker}_M5_sync_AI.csv'))
        df_h1 = standardize_df(pd.read_csv(f'bot/data/{ticker}_H1_sync_AI.csv'))
        
        forge = LiveGatedForge(ticker)
        
        pnl, history = [], []
        in_pos = False
        last_h1_time = None
        trades = 0
        
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
            
            # Map state history 1:1 with PnL array
            state = forge.state.copy()
            state['Time'] = current_time
            state['Close'] = row_m5['close']
            history.append(state)

        total_pnl = np.sum(pnl)
        hold = (df_m5['close'].iloc[-1] - df_m5['close'].iloc[100]) / df_m5['close'].iloc[100]
        
        # Drawdown Autopsy Logic
        max_dd = 0
        peak_state, trough_state = {}, {}
        
        if len(pnl) > 0:
            equity_curve = (1 + pd.Series(pnl)).cumprod()
            peak_series = equity_curve.cummax()
            drawdown_series = (equity_curve - peak_series) / peak_series
            
            trough_idx = drawdown_series.idxmin()
            if trough_idx > 0:
                peak_idx = equity_curve.iloc[:trough_idx+1].idxmax()
                max_dd = drawdown_series.min()
                
                peak_state = history[peak_idx]
                peak_state['Event'] = 'PEAK'
                peak_state['Equity'] = equity_curve.iloc[peak_idx]
                
                trough_state = history[trough_idx]
                trough_state['Event'] = 'TROUGH'
                trough_state['Equity'] = equity_curve.iloc[trough_idx]
            
        return total_pnl, hold, trades, max_dd, peak_state, trough_state
            
    except Exception as e:
        print(f'[{ticker} ERROR] {e}')
        return 0, 0, 0, 0, {}, {}

def run_portfolio_live_sim():
    tickers = ['AVGO', 'MSFT', 'NVDA']
    results = []
    print('\n=== LIVE-LOGIC PORTFOLIO RISK VERIFICATION ===')
    
    for t in tickers:
        pnl, hold, trades, mdd, peak, trough = run_live_simulation(t)
        alpha = pnl - hold
        results.append({
            'Ticker': t, 
            'Live PnL': f'{pnl:.2%}', 
            'Alpha': f'{alpha:.2%}',
            'Max DD': f'{mdd:.2%}',
            'Trades': trades
        })
        
        print(f'\n--- {t} DRAWDOWN AUTOPSY ---')
        if peak and trough:
            cols = ['Event', 'Time', 'Close', 'Equity', 'H1_Flux', 'H1_Tilt', 'Ceiling', 'M5_Rds', 'Signal']
            autopsy_df = pd.DataFrame([peak, trough])[cols]
            print(autopsy_df.to_string(index=False))
        else:
            print('No significant drawdown detected.')
        
    print('\n=== FINAL RISK & ALPHA RESULTS ===')
    print(pd.DataFrame(results).to_string(index=False))

if __name__ == '__main__':
    run_portfolio_live_sim()