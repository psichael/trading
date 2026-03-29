import pandas as pd
import numpy as np
from pathlib import Path

class LocalDataIngestor:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)

    def load_aligned_data(self, tickers, start_date=None, end_date=None):
        print(f"[SIM DATA] Ingesting {len(tickers)} assets from {self.data_dir}...")
        m5_master = pd.DataFrame()
        h1_map = {}
        d1_map = {}

        start_dt = pd.to_datetime(start_date).tz_localize(None) if start_date else None
        end_dt = pd.to_datetime(end_date).tz_localize(None) if end_date else None

        for t in tickers:
            # 1. M5 Timeline
            m5_path = self.data_dir / f"{t}_M5_sync_AI.csv"
            if m5_path.exists():
                try:
                    df = pd.read_csv(m5_path, parse_dates=['time']).set_index('time')
                    if df.index.tz is not None: df.index = df.index.tz_convert(None)
                    df = df[['close']].rename(columns={'close': t})
                    if start_dt: df = df[df.index >= start_dt]
                    if end_dt: df = df[df.index <= end_dt]
                    if not df.empty: m5_master = pd.concat([m5_master, df], axis=1)
                except Exception as e: print(f"[WARN] Failed to load M5 for {t}: {e}")

            # 2. H1 Physics Data
            h1_path = self.data_dir / f"{t}_H1_sync_AI.csv"
            if h1_path.exists():
                try:
                    df_h1 = pd.read_csv(h1_path, parse_dates=['time'])
                    if df_h1['time'].dt.tz is not None:
                        df_h1['time'] = df_h1['time'].dt.tz_convert(None)
                    if start_dt: df_h1 = df_h1[df_h1['time'] >= start_dt]
                    if end_dt: df_h1 = df_h1[df_h1['time'] <= end_dt]
                    
                    h1_map[t] = df_h1.sort_values('time').reset_index(drop=True)
                except Exception as e: print(f"[WARN] Failed to load H1 for {t}: {e}")

            # 3. D1 Macro Data (FIXED TO MATCH ORIGINAL SCRIPT MATH)
            d1_path = self.data_dir / f"{t}_D1_sync_AI.csv"
            if d1_path.exists():
                try:
                    df_d1 = pd.read_csv(d1_path, parse_dates=['time']).set_index('time')
                    if df_d1.index.tz is not None: df_d1.index = df_d1.index.tz_convert(None)
                    
                    # Exact D1 Flux math from run_dynamic_golden_list.py
                    df_d1['ret'] = df_d1['close'].pct_change()
                    df_d1['v_d1'] = df_d1['ret'].rolling(24).std() * 100 * np.sqrt(252)
                    df_d1['f_d'] = (df_d1['v_d1'] / 2.0) * 4.2525
                    df_d1['f_d'] = df_d1['f_d'].fillna(0)
                    
                    df_d1 = df_d1[['close', 'f_d']].rename(columns={'close': t})
                    d1_map[t] = df_d1
                except Exception as e: print(f"[WARN] Failed to load D1 for {t}: {e}")

        if m5_master.empty:
            return pd.DataFrame(), {}, {}
            
        return m5_master.sort_index().ffill(), h1_map, d1_map