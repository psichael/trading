import pandas as pd
from simulation.core.math_utils import get_friction

class SimBroker:
    def __init__(self, initial_capital, max_slots):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_slots = max_slots
        self.positions = {}
        self.history = []
        self.trade_count = 0
        
    @property
    def allocation_per_slot(self):
        """Dynamically calculate available capital per slot."""
        if self.max_slots == 1:
            return self.cash
        # Simple division for multi-slot, though real multi-slot is more complex
        return self.initial_capital / self.max_slots

    def get_holdings(self):
        return [ticker for ticker, shares in self.positions.items() if shares > 0]

    def get_estimated_portfolio_value(self, current_row):
        value = self.cash
        for ticker, shares in self.positions.items():
            if shares > 0 and not pd.isna(current_row.get(ticker)):
                value += shares * current_row[ticker]
        return value

    def execute(self, ticker, action, price):
        fric = get_friction(ticker)
        
        if action == 'BUY':
            usable_capital = self.allocation_per_slot * (1 - fric)
            # FIX: Remove int() cast to allow fractional compounding like original script
            shares = usable_capital / price
            
            if shares > 0 and self.cash >= (shares * price):
                self.positions[ticker] = shares
                cost = shares * price
                self.cash -= cost
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
        final_portfolio_value = self.cash
        
        for ticker, shares in self.positions.items():
            if shares > 0 and ticker in final_prices and not pd.isna(final_prices[ticker]):
                final_portfolio_value += shares * final_prices[ticker]
                
        roi = ((final_portfolio_value / self.initial_capital) - 1) * 100
        
        print("\n" + "="*50)
        print("=== 30-DAY WALK-FORWARD SIMULATION RESULTS ===")
        print(f"Starting Capital:  ${self.initial_capital:,.2f}")
        print(f"Ending Capital:    ${final_portfolio_value:,.2f}")
        print(f"Total ROI:         {roi:.2f}%")
        print(f"Total Trades:      {self.trade_count}")
        print("="*50 + "\n")