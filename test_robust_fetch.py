
import requests
import yfinance as yf
import pandas as pd

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

def test_robust_fetch():
    session = create_session()
    symbols = ['XU100.IS', 'TRY=X', 'EURTRY=X', 'GC=F']
    
    print("--- STARTING ROBUST FETCH TEST ---")
    data = {}
    
    for sym in symbols:
        print(f"Fetching {sym}...")
        try:
            ticker = yf.Ticker(sym, session=session)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                print(f"❌ {sym}: Empty")
            else:
                print(f"✅ {sym}: {len(hist)} rows. Last: {hist.iloc[-1]['Close']:.2f}")
                data[sym] = hist['Close']
                
        except Exception as e:
            print(f"❌ {sym}: Error {e}")

    if data:
        df = pd.DataFrame(data)
        print("\nCombined DataFrame Head:")
        print(df.head())
    else:
        print("❌ All failed.")

if __name__ == "__main__":
    test_robust_fetch()
