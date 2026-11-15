import random

def get_market_prices():
    """
    Simulates or fetches real-time prices for EUR/USD, DXY, and US10Y.
    Replace with actual APIs (e.g., Alpha Vantage, Yahoo Finance, or Forex API) in production.
    """
    # Mock data structure for demonstration
    data = {
        "EURUSD": 1.0850,
        "DXY": 104.20,
        "DXY_change_percent": 0.35,  # e.g. > 0.3% triggers intraday update
        "US10Y": 4.25,
        "US10Y_change_bps": 6.0      # e.g. > 5 bps triggers intraday update
    }
    return data

def check_intraday_triggers() -> list:
    """
    Checks if DXY or US10Y have crossed the threshold for an intraday update alert.
    - DXY moves > 0.3%
    - US10Y moves > 5 bps
    """
    market = get_market_prices()
    triggers = []
    
    if abs(market["DXY_change_percent"]) >= 0.3:
        triggers.append(f"DXY moved {market['DXY_change_percent']}% in the session.")
        
    if abs(market["US10Y_change_bps"]) >= 5.0:
        triggers.append(f"US10Y yields shifted by {market['US10Y_change_bps']} basis points.")
        
    return triggers