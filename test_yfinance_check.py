
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')

print(f"Testing yfinance download from {start} to {end}...")

try:
    # Test USD
    print("\nAttempting USDTRY=X...")
    df_usd = yf.download("USDTRY=X", start=start, end=end, progress=False)
    print(f"USDTRY shape: {df_usd.shape}")
    if not df_usd.empty:
        print(df_usd.head(2))
    else:
        print("USDTRY is empty!")

    # Test BIST
    print("\nAttempting XU100.IS...")
    df_bist = yf.download("XU100.IS", start=start, end=end, progress=False)
    print(f"BIST shape: {df_bist.shape}")
    if not df_bist.empty:
        print(df_bist.head(2))
    else:
        print("BIST is empty!")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
