
import yfinance as yf
import pandas as pd

print("--- YFINANCE DEBUG ---")
symbols = ['XU100.IS', 'TRY=X', 'EURTRY=X', 'GC=F']
print(f"Fetching: {symbols}")

try:
    df = yf.download(symbols, period="1mo", progress=False)
    print("\n[INFO] Data Downloaded")
    print("Columns:", df.columns)
    print("Shape:", df.shape)
    print("\nHead:\n", df.head())
    
    print("\n[INFO] Checking MultiIndex")
    if isinstance(df.columns, pd.MultiIndex):
        print("Detected MultiIndex columns")
        print("Level 0:", df.columns.levels[0])
        print("Level 1:", df.columns.levels[1])
        
        try:
            df_close = df['Close']
            print("\nSuccessfully accessed df['Close']")
            print(df_close.head())
        except KeyError:
            print("\nFAILED to access df['Close']")
            
        try:
            df_adj = df['Adj Close']
            print("\nSuccessfully accessed df['Adj Close']")
            print(df_adj.head())
        except KeyError:
            print("\nFAILED to access df['Adj Close']")

    else:
        print("Not MultiIndex")

except Exception as e:
    print(f"\n[ERROR] Download failed: {e}")
