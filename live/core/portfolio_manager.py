import pandas as pd
from live.core.math_utils import get_friction, get_regime

class PortfolioManager:
    def __init__(self, assets, max_slots):
        self.assets = assets
        self.max_slots = max_slots
        self.golden_list = []
        self.active_roster = []
        
        # Exact Backtest Parameters
        self.draft_size = 30
        self.max_sector_weight = 0.15
        self.hedge_quota = 0.20
        self.lookback_days = 30

    def rebuild_golden_list(self, current_time, daily_master):
        """
        MACRO FILTER: Runs Quarterly (every 13 weeks).
        Averages the last 30 days of daily flux (f_d) and applies strict regime capping.
        """
        print(f"\n[PORTFOLIO] {current_time.strftime('%Y-%m-%d')} - Rebuilding Quarterly Golden List...")
        screener_scores = {}
        screen_start = current_time - pd.DateOffset(days=self.lookback_days)
        
        for t in self.assets:
            df = daily_master.get(t)
            if df is not None and not df.empty:
                # Mask out future data to prevent lookahead bias
                mask = (df.index >= screen_start) & (df.index < current_time)
                screen_data = df[mask]
                
                # Require at least 50% of the lookback period to have valid data
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
            if regime_counts[reg] < max_per_regime:
                new_golden_list.append(t)
                regime_counts[reg] += 1
                
        # Fill strictly designated hedge slots
        if hedge_slots > 0:
            defensive_candidates = [t for t in sorted_tickers if get_regime(t) == 'Defensive_Macro' and t not in new_golden_list]
            for t in defensive_candidates:
                if len(new_golden_list) >= self.draft_size: 
                    break
                new_golden_list.append(t)
        
        self.golden_list = new_golden_list

    def rebuild_active_roster(self, current_time, daily_master):
        """
        MESO FILTER: Runs Weekly.
        Drafts the Top 5 from the Golden List based on the immediate f_d score.
        Applies a 1.15x modifier to incumbent assets to prevent whiplash.
        """
        if not self.golden_list:
            return

        print(f"[PORTFOLIO] {current_time.strftime('%Y-%m-%d')} - Drafting Weekly Active Roster...")
        scores = {}
        
        for t in self.golden_list:
            df = daily_master.get(t)
            # Mask out future data
            past_df = df[df.index <= current_time] if df is not None else None
            
            if past_df is not None and not past_df.empty:
                raw_flux = past_df['f_d'].iloc[-1]
            else:
                raw_flux = 0.0
                
            # Severe 100x friction penalty for daily sorting
            score = raw_flux * (1 - (get_friction(t) * 100))
            
            # The Incumbent Modifier
            if t in self.active_roster: 
                score *= 1.15
                
            scores[t] = score
            
        self.active_roster = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:self.max_slots]
        print(f"[PORTFOLIO LOCK] Active Targets: {self.active_roster}")

    def check_exit_condition(self, ticker, held_tickers, forges):
        """
        MICRO EXECUTION: Runs every 5 minutes.
        Determines if an owned asset should be liquidated based on Forge states.
        """
        current_sig = forges[ticker].get_signal()
        current_flux = forges[ticker].state.get('H1_Flux', 0)
        force_exit = False
        
        # 1. Standard Exit: The Manifold fractures
        if current_sig == 'WAIT': 
            force_exit = True
        else:
            # 2. The 1.5x Override Exit: A significantly better asset is calling LONG
            # Find all active roster assets that are LONG but not currently owned
            cands = [t for t in self.active_roster if forges[t].get_signal() == 'LONG' and t != ticker and t not in held_tickers]
            
            if cands:
                # Find the best candidate using the lighter 10x intraday friction penalty
                best_alt = max(cands, key=lambda t: forges[t].state.get('H1_Flux', 0) * (1 - (get_friction(t) * 10)))
                
                # Trigger the exit ONLY if the alternative is 1.5x better (plus friction variance)
                if forges[best_alt].state.get('H1_Flux', 0) > (current_flux * (1.5 + (get_friction(best_alt) * 100))):
                    print(f"[{ticker}] 1.5x Override Triggered. Making room for {best_alt}.")
                    force_exit = True
                    
        return force_exit