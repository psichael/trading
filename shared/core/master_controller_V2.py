import pandas as pd
import numpy as np
# Fallback to the live version of the sanity check until it is migrated
from live.core.hourly_sanity_check import get_tilt

class LiveGatedForge:
    def __init__(self, ticker):
        self.ticker = ticker
        self.m5_closes = []
        self.h1_closes = []
        self.h1_flux_history = []
        self.tilt_ceiling = 1.25
        self.last_h1_len = 0
        self.state = {}
        
        # Time-Physics Patch: 24/5 & 24/7 markets vs 6.5h equities
        t_upper = ticker.upper()
        is_24h = any(x in t_upper for x in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'BNB', 'LINK', 'MATIC', 'AVAX'])
        self.bars_per_day = 288 if is_24h else 78

    def ingest_m5(self, close_price):
        self.m5_closes.append(close_price)
        if len(self.m5_closes) > 80: self.m5_closes.pop(0)

    def ingest_h1(self, close_price):
        self.h1_closes.append(close_price)
        if len(self.h1_closes) > 500: self.h1_closes.pop(0)

    def get_signal(self):
        if len(self.h1_closes) < 25 or len(self.m5_closes) < 79:
            self.state = {'Signal': 'WAIT_WARMUP'}
            return 'WAIT_WARMUP'

        # M5 Math (Dynamically Annualized)
        m5_s = pd.Series(self.m5_closes).pct_change().dropna()
        v_m5 = m5_s.std() * 100 * np.sqrt(252 * self.bars_per_day)
        f_m5 = (v_m5 / 4.5) * 4.5
        rds = 1.0 + (4.06 * np.exp(-0.85 * (f_m5 - 2.14))) if f_m5 >= 2.14 else 5.06

        # H1 Math
        h1_s = pd.Series(self.h1_closes)
        h1_ret = h1_s.pct_change().dropna()
        v_h1 = h1_ret.rolling(24).std().dropna() * 100 * np.sqrt(252)
        
        if len(v_h1) < 1: 
            self.state = {'Signal': 'WAIT_WARMUP'}
            return 'WAIT_WARMUP'
        
        f_h = (v_h1.iloc[-1] / 2.0) * 4.2525
        
        if len(self.h1_closes) > self.last_h1_len:
            self.h1_flux_history.append(f_h)
            if len(self.h1_flux_history) > 500: self.h1_flux_history.pop(0)
            self.last_h1_len = len(self.h1_closes)

        t_h = get_tilt(f_h, 3.5)
        sma_24 = h1_s.rolling(24).mean().iloc[-1]
        
        flux_ceiling = np.median(self.h1_flux_history) * 1.5 if len(self.h1_flux_history) > 24 else 45.0
        
        # DIRECTIONAL FILTERING
        h1_trend_up = self.h1_closes[-1] > sma_24
        
        m_stable = (t_h < self.tilt_ceiling) and (f_h <= flux_ceiling) and h1_trend_up
        escape_velocity = (f_h > flux_ceiling) and h1_trend_up
        
        signal = 'LONG' if ((m_stable or escape_velocity) and (rds < 1.04)) else 'WAIT'
        
        self.state = {
            'H1_Flux': round(f_h, 2),
            'H1_Tilt': round(t_h, 4),
            'Ceiling': round(flux_ceiling, 2),
            'M5_Rds': round(rds, 4),
            'M5_Flux': round(f_m5, 4),
            'Signal': signal
        }
        return signal