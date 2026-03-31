import pandas as pd
import numpy as np
from simulation.data_code.cache_manager import DataCacheManager

class TiingoSimAdapter:
    def __init__(self, tickers, token):
        self.cache = DataCacheManager(tickers, token)
        self.tickers = tickers

    def get_simulation_data(self):
        """
        Fetches Tiingo data and transforms it into the M5, H1, and D1 
        formats required by the simulation engine.
        """
        print(f"🌐 [TIINGO ADAPTER] Synchronizing Unified Data Lake...")
        # 1. Get the Master M5 Timeline (The 'Matter')
        m5_master = self.cache.sync_and_load_history()
        
        h1_map = {}
        d1_map = {}

        print(f"📊 [TIINGO ADAPTER] Resampling Physics Manifolds (H1/D1)...")
        for t in self.tickers:
            # 2. Derive H1 Physics Map from M5 to ensure 100% alignment
            df_h1 = m5_master[[t]].resample('1h').last().dropna()
            df_h1 = df_h1.reset_index().rename(columns={'index': 'time', t: 'close'})
            h1_map[t] = df_h1

            # 3. Derive D1 Macro Map using the cache_manager's daily_master logic
            if t in self.cache.daily_master.index.get_level_values('ticker'):
                ticker_d1 = self.cache.daily_master.xs(t, level='ticker').copy()
                # Re-insert 'close' for the portfolio manager's golden_list logic
                daily_closes = m5_master[t].resample('D').last()
                ticker_d1['close'] = daily_closes
                d1_map[t] = ticker_d1.dropna()

        return m5_master, h1_map, d1_map