import pandas as pd
import numpy as np
from bot.hourly_sanity_check import get_tilt

def standardize_df(df):
    for col in df.columns:
        if any(key in col.lower() for key in ['time', 'date', 'stamp']):
            df = df.copy()
            df['time'] = pd.to_datetime(df[col], utc=True)
            return df
    return df

def simulate_asset(ticker):
    TAX = 0.0001
    try:
        df_m5 = standardize_df(pd.read_csv(f'bot/data/{ticker}_M5_sync_AI.csv'))
        df_h1 = standardize_df(pd.read_csv(f'bot/data/{ticker}_H1_sync_AI.csv'))

        df_m5['ret'] = df_m5['close'].pct_change()
        df_m5['v'] = df_m5['ret'].rolling(78).std() * 100 * np.sqrt(252*78)
        
        df_h1['ret'] = df_h1['close'].pct_change()
        df_h1['v_ann'] = df_h1['ret'].rolling(24).std() * 100 * np.sqrt(252)
        df_h1['f'] = (df_h1['v_ann'] / 2.0) * 4.2525
        df_h1['sma_24'] = df_h1['close'].rolling(24).mean()
        
        flux_ceiling = df_h1['f'].median() * 1.5
        tilt_ceiling = 1.25

        pnl, in_pos = [], False
        
        for i in range(100, len(df_m5)):
            row_m5 = df_m5.iloc[i]
            valid_h1 = df_h1[df_h1['time'] <= row_m5['time']]
            if valid_h1.empty: continue
            h1_row = valid_h1.iloc[-1]
            
            f_h, t_h = h1_row['f'], get_tilt(h1_row['f'], 3.5)
            m_stable = (t_h < tilt_ceiling) and (f_h <= flux_ceiling)
            
            h1_trend_up = h1_row['close'] > h1_row['sma_24']
            escape_velocity = (f_h > flux_ceiling) and h1_trend_up
            
            f_m5 = (row_m5['v'] / 4.5) * 4.5
            rds = 1.0 + (4.06 * np.exp(-0.85 * (f_m5 - 2.14))) if f_m5 >= 2.14 else 5.06
            
            signal = (m_stable or escape_velocity) and (rds < 1.04)

            r = 0
            if signal:
                r = row_m5['ret']
                if not in_pos: r -= TAX; in_pos = True
                pnl.append(r)
            else:
                if in_pos: pnl.append(-TAX); in_pos = False
                else: pnl.append(0)

        total_pnl = np.sum(pnl)
        hold = (df_m5['close'].iloc[-1] - df_m5['close'].iloc[100]) / df_m5['close'].iloc[100]
        return total_pnl, hold, (total_pnl - hold)
    except Exception as e:
        print(f'[{ticker} ERROR] {e}')
        return 0, 0, 0

def run_portfolio():
    tickers = ['NVDA', 'AVGO', 'MSFT']
    results = []
    print('\n=== PORTFOLIO RIGIDITY & ALPHA SIMULATION (WITH ESCAPE VELOCITY) ===')
    for t in tickers:
        forge, hold, alpha = simulate_asset(t)
        results.append({'Ticker': t, 'Forge PnL': f'{forge:.2%}', 'Hold PnL': f'{hold:.2%}', 'Alpha': f'{alpha:.2%}'})
    
    print(pd.DataFrame(results).to_string(index=False))

if __name__ == '__main__':
    run_portfolio()