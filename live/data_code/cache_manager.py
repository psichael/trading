import os
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

class DataCacheManager:
    def __init__(self, assets, token):
        self.assets = assets
        self.token = token
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data_code', 'history')
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, 'history.csv')
        self.daily_master = pd.DataFrame()

    def fetch_with_feedback(self, url, params, ticker):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 429:
                print(f"⚠️ [TIINGO LIMIT] Rate limit hit for {ticker}. Check Power Tier usage.")
                return None
            if response.status_code == 403:
                print(f"🚫 [TIINGO AUTH] 403 Forbidden for {ticker}. Check IEX Entitlements.")
                return None
            if response.status_code != 200:
                print(f"❌ [TIINGO ERR] {ticker} {response.status_code}: {response.text[:100]}")
                return None
            return response.json()
        except Exception as e:
            print(f"❌ [CONN ERR] Could not reach Tiingo for {ticker}: {e}")
            return None

    def fetch_surgical_slice(self, ticker, start_date, end_date=None):
        is_crypto = any(x in ticker.lower() for x in ['usd', 'btc', 'eth', 'sol', 'ada', 'dot', 'doge', 'avax'])
        url = f"https://api.tiingo.com/tiingo/crypto/prices" if is_crypto else f"https://api.tiingo.com/iex/{ticker}/prices"
        
        params = {'startDate': start_date, 'resampleFreq': '5min', 'token': self.token}
        if end_date: params['endDate'] = end_date
        if is_crypto: params['tickers'] = ticker

        data = self.fetch_with_feedback(url, params, ticker)
        if not data: return pd.DataFrame()

        raw_data = data[0]['priceData'] if is_crypto else data
        if not raw_data: return pd.DataFrame()
        
        df = pd.DataFrame(raw_data)
        date_col = 'date' if 'date' in df.columns else 'timestamp'
        df[date_col] = pd.to_datetime(df[date_col]).dt.tz_localize(None)
        df = df.rename(columns={date_col: 'timestamp', 'close': ticker})
        return df[['timestamp', ticker]].set_index('timestamp')

    def sync_and_load_history(self):
        print(f"🔍 [SYSTEM] Auditing Data Lake Integrity...")
        
        if os.path.exists(self.history_file):
            master_df = pd.read_csv(self.history_file, index_col=0, parse_dates=True)
            master_df.index = master_df.index.tz_localize(None)
        else:
            master_df = pd.DataFrame()

        now = datetime.now()
        start_threshold = (now - timedelta(days=60)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        perfect_idx = pd.date_range(start=start_threshold, end=now, freq='5min')
        master_df = master_df.reindex(perfect_idx)
        
        all_updates = []
        total_downloaded = 0
        
        for ticker in self.assets:
            series = master_df[ticker] if ticker in master_df.columns else pd.Series(index=perfect_idx, dtype='float64')
            missing_times = series.index[series.isna()]

            if missing_times.empty:
                print(f"✅ {ticker} is 100% healthy.")
                continue

            gaps = []
            gap_start = missing_times[0]
            for i in range(1, len(missing_times)):
                if (missing_times[i] - missing_times[i-1]).total_seconds() > 300:
                    gaps.append((gap_start, missing_times[i-1]))
                    gap_start = missing_times[i]
            gaps.append((gap_start, missing_times[-1]))

            for g_start, g_end in gaps:
                if (g_end - g_start).total_seconds() < 900: continue
                
                print(f"🩹 [HEAL] {ticker}: {g_start.strftime('%m-%d %H:%M')} -> {g_end.strftime('%m-%d %H:%M')}")
                slice_df = self.fetch_surgical_slice(ticker, g_start.strftime('%Y-%m-%d %H:%M:%S'), g_end.strftime('%Y-%m-%d %H:%M:%S'))
                
                if not slice_df.empty:
                    all_updates.append(slice_df)
                    total_downloaded += len(slice_df)
                time.sleep(0.1)

        if all_updates:
            print(f"🧵 [STITCH] Merging {len(all_updates)} pulses into Data Lake...")
            updates_df = pd.concat(all_updates, axis=0).sort_index()
            updates_df = updates_df.groupby(updates_df.index).first()
            master_df = master_df.combine_first(updates_df)
            master_df = master_df.sort_index().ffill().tail(30000)
            master_df.to_csv(self.history_file)

        print(f"📊 [PHYSICS] Deriving Daily Context (f_d)...")
        daily_prices = master_df.resample('D').last().dropna(how='all')
        daily_returns = np.log(daily_prices / daily_prices.shift(1))
        daily_flux = daily_returns.rolling(window=20).std().stack().reset_index()
        daily_flux.columns = ['date', 'ticker', 'f_d']
        self.daily_master = daily_flux.set_index(['ticker', 'date']).sort_index()
        
        print(f"✅ [LAKE READY] {len(master_df)} intervals synced ({total_downloaded} new intervals downloaded).")
        return master_df

    def fetch_live_tick(self):
        results = {}
        crypto_list = [t for t in self.assets if any(x in t.lower() for x in ['usd', 'btc', 'sol', 'doge', 'ada', 'dot', 'avax'])]
        if crypto_list:
            # Tiingo restricts crypto batches to 5 tickers maximum.
            for i in range(0, len(crypto_list), 5):
                chunk = crypto_list[i:i+5]
                url = f"https://api.tiingo.com/tiingo/crypto/prices?tickers={','.join(chunk)}&token={self.token}"
                data = self.fetch_with_feedback(url, {}, f"CryptoBatch-{i//5}")
                if isinstance(data, list):
                    for item in data:
                        t, pd_list = item.get('ticker'), item.get('priceData')
                        if t and pd_list and len(pd_list) > 0:
                            results[t] = pd_list[0].get('last') or pd_list[0].get('close')
        
        for ticker in self.assets:
            if ticker not in results:
                url = f"https://api.tiingo.com/iex/{ticker}?token={self.token}"
                data = self.fetch_with_feedback(url, {}, ticker)
                if isinstance(data, list) and len(data) > 0:
                    results[ticker] = data[0].get('tngoLast') or data[0].get('last')
        return results
