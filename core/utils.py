# -*- coding: utf-8 -*-
import pandas as pd
import yfinance as yf
import requests
import time

def get_robust_session():
    """
    Creates a requests Session with a browser-like User-Agent to avoid 403 Forbidden.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    })
    return session

def fetch_symbol_robust(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Attempts to fetch history for a single symbol using multiple strategies.
    1. yf.Ticker(sym, session=s).history()
    2. yf.Ticker(sym).history() (Fallback)
    
    Returns standard history DataFrame or Empty DataFrame.
    """
    session = get_robust_session()
    
    # Strategy 1: Ticker with Session (Best for 403s)
    try:
        # Note: Some old yfinance versions throw TypeError for 'session'
        ticker = yf.Ticker(symbol, session=session)
        df = ticker.history(period=period, interval=interval)
        if not df.empty:
            return df
    except TypeError:
        # Warning: Session not supported in this version
        pass 
    except Exception as e:
        print(f"Strategy 1 failed for {symbol}: {e}")
    
    # Strategy 2: Standard Ticker (Fallback)
    try:
        time.sleep(0.5)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if not df.empty:
            return df
    except Exception as e:
        print(f"Strategy 2 failed for {symbol}: {e}")

    # Strategy 3: Simple Download (Proven to work in v1.0)
    try:
        time.sleep(0.5)
        # Note: auto_adjust=True helps in some versions
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if not df.empty:
            return df
    except Exception as e:
         print(f"Strategy 3 failed for {symbol}: {e}")
        
    return pd.DataFrame()
