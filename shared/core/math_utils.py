def get_friction(ticker):
    """
    Returns the estimated slippage and fee friction for a given asset.
    """
    ticker = ticker.upper()
    
    if ticker in ['BTCUSD', 'ETHUSD', 'BTCUSDT', 'ETHUSDT', 'BTC', 'ETH']:
        return 0.0015
        
    # Prioritize altcoin friction before checking for USD currency strings
    elif any(crypto in ticker for crypto in ['SOL', 'ADA', 'DOGE', 'XRP', 'AVAX', 'MATIC', 'LINK', 'BNB', 'LTC', 'BCH', 'UNI', 'DOT', 'FIL', 'ETC']):
        return 0.0025
        
    # Only apply forex friction if it's a pure forex pair (length exactly 6, no crypto base)
    elif len(ticker) == 6 and any(fx in ticker for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']):
        return 0.0002
        
    else:
        # Standard Equities default to 0.0002 friction.
        return 0.0002

def get_regime(ticker):
    """
    Maps an asset to its macro-economic regime.
    """
    ticker = ticker.upper()
    
    if any(crypto in ticker for crypto in ['BTC', 'ETH', 'SOL', 'ADA', 'DOGE', 'XRP', 'AVAX', 'MATIC', 'LINK', 'BNB', 'LTC', 'BCH', 'UNI', 'DOT', 'FIL', 'ETC']):
        return 'Crypto'
        
    elif len(ticker) == 6 and any(fx in ticker for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']):
        return 'Forex'
        
    # Commodity Proxies (Miners & Producers)
    elif ticker in ['NEM', 'PAAS', 'FCX', 'XOM', 'CCJ', 'XLE', 'XLB']:
        return 'Commodities'
        
    # Defensive Macro Proxies (Utilities, Banks, Retail, Volatility, Broad Econ)
    elif ticker in ['NEE', 'CBOE', 'V', 'META', 'CAT', 'WMT', 'LLY', 'JPM']:
        return 'Defensive_Macro'
        
    else:
        # Default Equities (Tech/Growth)
        return 'Equities'