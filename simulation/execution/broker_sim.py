import pandas as pd
from simulation.core.math_utils import get_friction

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

class SimBroker:
    def __init__(self, initial_capital, max_slots):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_slots = max_slots
        self.positions = {}
        self.history = []
        self.trade_count = 0
        self.equity_log = []
        
    @property
    def allocation_per_slot(self):
        if self.max_slots == 1:
            return self.cash
        return self.initial_capital / self.max_slots

    def get_holdings(self):
        return [ticker for ticker, shares in self.positions.items() if shares > 0]

    def get_estimated_portfolio_value(self, current_row):
        value = self.cash
        missing_price = False
        
        for ticker, shares in self.positions.items():
            if shares > 0:
                price = current_row.get(ticker)
                if pd.notna(price) and price > 0:
                    value += shares * price
                else:
                    missing_price = True
                    
        # Fallback to the last known equity if a data gap occurs
        if missing_price and self.equity_log:
            return self.equity_log[-1]['equity']
            
        return value

    def record_equity(self, current_time, current_row):
        val = self.get_estimated_portfolio_value(current_row)
        self.equity_log.append({'time': current_time, 'equity': val})

    def execute(self, ticker, action, price):
        fric = get_friction(ticker)
        
        if action == 'BUY':
            usable_capital = self.allocation_per_slot * (1 - fric)
            shares = usable_capital / price
            
            actual_cost = shares * price
            total_deduction = actual_cost / (1 - fric) # Deduct cost + the broker fee
            
            # Use a tiny epsilon to prevent float math rejection on full-cash deployments
            if shares > 0 and self.cash >= (total_deduction - 1e-6):
                self.positions[ticker] = shares
                self.cash -= total_deduction
                if self.cash < 0: 
                    self.cash = 0.0 # Prevent -0.000001 balances
                    
                self.trade_count += 1
                self.history.append(f"BUY {shares:.4f} {ticker} @ ${price:.2f} | Fee: {(fric*100):.2f}%")
                return True
            return False
                
        elif action == 'SELL':
            shares = self.positions.get(ticker, 0)
            if shares > 0:
                revenue = (shares * price) * (1 - fric)
                self.cash += revenue
                self.positions[ticker] = 0
                self.trade_count += 1
                self.history.append(f"SELL {shares:.4f} {ticker} @ ${price:.2f} | Fee: {(fric*100):.2f}%")
                return True
        return False

    def print_results(self, final_prices):
        # Centralized logic ensures missing prices don't cause CLI output bugs
        final_portfolio_value = self.get_estimated_portfolio_value(final_prices)
                
        roi = ((final_portfolio_value / self.initial_capital) - 1) * 100
        
        print("\n" + "="*50)
        print("=== SIMULATION RESULTS ===")
        print(f"Starting Capital:  ${self.initial_capital:,.2f}")
        print(f"Ending Capital:    ${final_portfolio_value:,.2f}")
        print(f"Total ROI:         {roi:.2f}%")
        print(f"Total Trades:      {self.trade_count}")
        print("="*50 + "\n")

    def generate_tearsheet(self, warmup_end=None, filename="tearsheet.png"):
        if not plt:
            print("⚠️  Matplotlib not installed. Skipping tearsheet generation. Run: pip install matplotlib")
            return
        if not self.equity_log:
            return
            
        df = pd.DataFrame(self.equity_log).set_index('time')
        final_val = df['equity'].iloc[-1]
        roi = ((final_val / self.initial_capital) - 1) * 100
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df.index, df['equity'], color='#00ffcc', linewidth=2, label='Portfolio Value')
        
        if warmup_end:
            ax.axvline(x=warmup_end, color='white', linestyle='--', alpha=0.5, label='Trading Activated')
            
        ax.set_title(f"Simulation Tearsheet | Final ROI: {roi:.2f}% | Trades: {self.trade_count}")
        ax.set_ylabel("Capital ($)")
        ax.grid(color='gray', linestyle='-', linewidth=0.25, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300)
        print(f"📊 Tearsheet successfully rendered to: {filename}\n")
        plt.close()