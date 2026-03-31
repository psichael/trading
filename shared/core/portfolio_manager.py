import pandas as pd
from shared.core.math_utils import get_friction, get_regime

class PortfolioManager:
    def __init__(self, assets, max_slots, lookback_days=30, draft_size=30, max_sector_weight=0.15, hedge_quota=0.20):
        self.assets = assets
        self.max_slots = max_slots
        self.active_roster_size = 5
        self.golden_list = []
        self.active_roster = []
        
        self.draft_size = draft_size
        self.max_sector_weight = max_sector_weight
        self.hedge_quota = hedge_quota
        self.lookback_days = lookback_days

    def rebuild_golden_list(self, current_time, daily_master):
        print(f"\n[PORTFOLIO] {current_time.strftime('%Y-%m-%d')} - Rebuilding Quarterly Golden List...")
        screener_scores = {}
        screen_start = current_time - pd.DateOffset(days=self.lookback_days)
        
        for t in self.assets:
            df = daily_master.get(t)
            if df is not None and not df.empty:
                mask = (df.index >= screen_start) & (df.index < current_time)
                screen_data = df[mask]
                if len(screen_data) > (self.lookback_days * 0.5):
                    avg_flux = screen_data['f_d'].mean()
                    screener_scores[t] = avg_flux * (1 - (get_friction(t) * 100))
                else:
                    screener_scores[t] = 0.0
            else:
                screener_scores[t] = 0.0
                
        sorted_tickers = sorted(screener_scores.keys(), key=lambda x: screener_scores[x], reverse=True)
        
        new_golden_list = []
        regime_counts = {'Crypto': 0, 'Forex': 0, 'Commodities': 0, 'Defensive_Macro': 0, 'Equities': 0}
        max_per_regime = int(self.draft_size * self.max_sector_weight)
        hedge_slots = int(self.draft_size * self.hedge_quota)
        
        for t in sorted_tickers:
            if len(new_golden_list) >= (self.draft_size - hedge_slots): 
                break
            reg = get_regime(t)
            if regime_counts.get(reg, 0) < max_per_regime:
                new_golden_list.append(t)
                regime_counts[reg] = regime_counts.get(reg, 0) + 1
                
        if hedge_slots > 0:
            defensive_candidates = [t for t in sorted_tickers if get_regime(t) == 'Defensive_Macro' and t not in new_golden_list]
            for t in defensive_candidates:
                if len(new_golden_list) >= self.draft_size: 
                    break
                new_golden_list.append(t)
        
        self.golden_list = new_golden_list

    def rebuild_active_roster(self, current_time, daily_master):
        if not self.golden_list:
            return
        print(f"[PORTFOLIO] {current_time.strftime('%Y-%m-%d')} - Drafting Weekly Active Roster...")
        scores = {}
        for t in self.golden_list:
            df = daily_master.get(t)
            past_df = df[df.index <= current_time] if df is not None else None
            raw_flux = past_df['f_d'].iloc[-1] if past_df is not None and not past_df.empty else 0.0
            score = raw_flux * (1 - (get_friction(t) * 100))
            if t in self.active_roster: 
                score *= 1.15
            scores[t] = score
            
        self.active_roster = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:self.active_roster_size]
        print(f"[PORTFOLIO LOCK] Active Targets: {self.active_roster}")

    def check_exit_condition(self, ticker, held_tickers, forges):
        current_sig = forges[ticker].get_signal()
        current_flux = forges[ticker].state.get('H1_Flux', 0)
        force_exit = False
        
        if current_sig == 'WAIT': 
            force_exit = True
        else:
            cands = [t for t in self.active_roster if forges[t].get_signal() == 'LONG' and t != ticker and t not in held_tickers]
            if cands:
                best_alt = max(cands, key=lambda t: forges[t].state.get('H1_Flux', 0) * (1 - (get_friction(t) * 10)))
                if forges[best_alt].state.get('H1_Flux', 0) > (current_flux * (1.5 + (get_friction(best_alt) * 100))):
                    print(f"[{ticker}] 1.5x Override Triggered. Making room for {best_alt}.")
                    force_exit = True
                    
        return force_exit