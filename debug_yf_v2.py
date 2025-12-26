import yfinance as yf
import pandas as pd

print("Testing yfinance download...")
symbols = ['XU100.IS', 'TRY=X', 'EURTRY=X', 'GC=F']

# Try 1: Standard
try:
    df = yf.download(symbols, period='5d', progress=False)
    print("\n--- Raw DataFrame Head ---")
    print(df.head())
    print("\n--- Columns ---")
    print(df.columns)
    
    if isinstance(df.columns, pd.MultiIndex):
        print("\n--- MultiIndex Detected ---")
        try:
            df_close = df['Close']
            print("Accessing ['Close'] works.")
            print(df_close.tail())
            
            # Check individual columns
            for s in symbols:
                if s in df_close.columns:
                    print(f"Symbol {s} FOUND in Close columns. Last val: {df_close[s].iloc[-1]}")
                else:
                    print(f"Symbol {s} NOT FOUND in Close columns.")
        except KeyError:
            print("KeyError when accessing 'Close'. Available levels:")
            print(df.columns.levels)
    else:
        print("\n--- Single Index ---")
        print(df.tail())

except Exception as e:
    print(f"Error: {e}")
