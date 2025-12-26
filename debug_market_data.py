import yfinance as yf
import pandas as pd

def test_market_data():
    symbols = ['XU100.IS', 'TRY=X', 'EURTRY=X', 'GC=F']
    print(f"Testing symbols: {symbols}")
    
    try:
        # Try fetching with 1d first
        print("\n--- Attempt 1: period='1d' ---")
        df = yf.download(symbols, period='1d', progress=False)
        print("Columns:", df.columns)
        print("Data:\n", df)
        
        if df.empty:
            print("❌ Result is empty.")
        else:
            print("✅ Data fetched.")

        # Try fetching with 5d to handle weekends
        print("\n--- Attempt 2: period='5d' ---")
        df5 = yf.download(symbols, period='5d', progress=False)
        print("Data (Tail):\n", df5.tail())
        
        # Check individual Close prices
        if not df5.empty:
            # Handle MultiIndex
            if isinstance(df5.columns, pd.MultiIndex):
                # Try to access Close
                try:
                    close_df = df5['Close']
                    print("\nClose Prices (Last Row):")
                    print(close_df.iloc[-1])
                except KeyError:
                    # Fallback for 'Adj Close'
                    print("\n'Close' not found, trying 'Adj Close'...")
                    close_df = df5['Adj Close']
                    print(close_df.iloc[-1])
            else:
                 print("\nSingle Level Columns:", df5.columns)

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_market_data()
