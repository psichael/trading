def get_friction(ticker):
    """
    Returns the estimated slippage and fee friction for a given asset.
    """
    ticker = ticker.upper()
    
    if ticker in ['BTCUSD', 'ETHUSD', 'BTCUSDT', 'ETHUSDT', 'BTC', 'ETH']:
        return 0.0015
        
    elif any(crypto in ticker for crypto in ['SOL', 'ADA', 'DOGE', 'XRP', 'AVAX', 'MATIC', 'LINK', 'BNB', 'LTC', 'BCH', 'UNI', 'DOT', 'FIL', 'ETC']):
        return 0.0025
        
    elif any(fx in ticker for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']):
        return 0.0002
        
    else:
        return 0.0002

def get_regime(ticker):
    """
    Maps an asset to its macro-economic regime.
    """
    ticker = ticker.upper()
    
    if any(crypto in ticker for crypto in ['BTC', 'ETH', 'SOL', 'ADA', 'DOGE', 'XRP', 'AVAX', 'MATIC', 'LINK', 'BNB', 'LTC', 'BCH', 'UNI', 'DOT', 'FIL', 'ETC']):
        return 'Crypto'
        
    elif any(fx in ticker for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']):
        return 'Forex'
        
    elif ticker in ['NEM', 'PAAS', 'FCX', 'XOM', 'CCJ', 'XLE', 'XLB']:
        return 'Commodities'
        
    elif ticker in ['NEE', 'CBOE', 'V', 'META', 'CAT', 'WMT', 'LLY', 'JPM']:
        return 'Defensive_Macro'
        
    else:
        return 'Equities'