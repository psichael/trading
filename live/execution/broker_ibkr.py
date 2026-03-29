import asyncio
import pytz
from datetime import datetime
from ib_async import IB, Stock, Crypto, LimitOrder
from live.core.math_utils import get_friction

class IBKRBroker:
    def __init__(self, max_slots, allocation_per_slot):
        self.ib = IB()
        self.max_slots = max_slots
        self.allocation_per_slot = allocation_per_slot
        self.est_tz = pytz.timezone('US/Eastern')

    def is_market_open(self):
        """Checks if the US Equity market is currently open (9:31 AM - 4:00 PM EST, Mon-Fri)."""
        now_est = datetime.now(self.est_tz)
        
        if now_est.weekday() > 4:
            return False
            
        market_open = now_est.replace(hour=9, minute=31, second=0, microsecond=0)
        market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_est <= market_close

    async def connect(self, host, port, clientId):
        """Establishes connection to the IB Gateway."""
        await self.ib.connectAsync(host, port, clientId=clientId)

    def disconnect(self):
        """Safely severs the IBKR connection."""
        if self.ib.isConnected():
            self.ib.disconnect()

    def get_holdings(self):
        """Queries the live IBKR account for current positions and maps them back to our ticker format."""
        positions = self.ib.positions()
        held_tickers = []
        for p in positions:
            if p.position > 0:
                if p.contract.secType == 'CRYPTO':
                    held_tickers.append(p.contract.symbol + 'USD')
                else:
                    held_tickers.append(p.contract.symbol)
        return held_tickers

    async def execute(self, ticker, action, price):
        """Builds the IBKR contract, calculates share size, and routes a Marketable Limit Order."""
        is_crypto = 'USD' in ticker
        
        # --- MARKET HOURS SAFETY VALVE ---
        if not is_crypto and not self.is_market_open():
            print(f"[{ticker}] 🛑 LIVE {action} BLOCKED: US Equity Market is currently closed or in Opening Cross.")
            return False
        
        # 1. Map Contract
        if is_crypto:
            clean_ticker = ticker.replace('USD', '')
            contract = Crypto(clean_ticker, 'PAXOS', 'USD')
        else:
            contract = Stock(ticker, 'SMART', 'USD')
            
        try:
            await self.ib.qualifyContractsAsync(contract)
        except Exception as e:
            print(f"[{ticker}] LIVE EXECUTION ERROR: Contract qualification failed. ({e})")
            return False
            
        fric = get_friction(ticker)
        
        # 2. Route Action using Marketable Limit Orders
        if action == 'BUY':
            if price <= 0:
                print(f"[{ticker}] LIVE BUY FAILED: Invalid price (${price}).")
                return False
                
            usable_capital = self.allocation_per_slot * (1 - fric)
            shares = int(usable_capital / price)
            
            if shares > 0:
                # Add 0.5% buffer to Tiingo price to guarantee execution
                limit_price = round(price * 1.005, 2)
                print(f"[LIVE IBKR] Routing BUY: {shares} {ticker} @ Limit ${limit_price:.2f} (Tiingo: ${price:.2f})")
                
                order = LimitOrder('BUY', shares, limit_price)
                order.tif = 'DAY' # Explicitly set TIF to clear the 10349 warning
                self.ib.placeOrder(contract, order)
                await asyncio.sleep(1)
                return True
            else:
                print(f"[{ticker}] LIVE BUY SKIPPED: Capital (${usable_capital:.2f}) insufficient for 1 share @ ${price:.2f}")
                return False
                
        elif action == 'SELL':
            positions = self.ib.positions()
            # Wrap in int() to strictly prevent fractional share routing errors
            shares_owned = int(sum(p.position for p in positions if p.contract.symbol == contract.symbol))
            
            if shares_owned > 0:
                # Subtract 0.5% buffer to Tiingo price to guarantee execution
                limit_price = round(price * 0.995, 2)
                print(f"[LIVE IBKR] Routing SELL: {shares_owned} {ticker} @ Limit ${limit_price:.2f} (Tiingo: ${price:.2f})")
                
                order = LimitOrder('SELL', shares_owned, limit_price)
                order.tif = 'DAY'
                self.ib.placeOrder(contract, order)
                await asyncio.sleep(1)
                return True
            else:
                print(f"[{ticker}] LIVE SELL SKIPPED: No shares found in IBKR portfolio.")
                return False
                
        return False
