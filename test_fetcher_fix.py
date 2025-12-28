
import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from core.market_fetcher import MarketFetcher

print("--- TESTING MARKET FETCHER FIX ---")
try:
    mf = MarketFetcher()
    df = mf.fetch_market_history()
    
    print("\n[RESULT]")
    if df.empty:
        print("❌ Still Empty!")
    else:
        print(f"✅ Data Fetched! Shape: {df.shape}")
        print("Columns:", df.columns.tolist())
        print("\nHead:\n", df.head())
        
        expected_cols = ['BIST 100', 'Dolar/TL', 'Euro/TL', 'Gram Altın']
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
             print(f"⚠️ Missing Columns: {missing}")
        else:
             print("✅ All Expected Columns Present.")

except Exception as e:
    print(f"❌ Crash: {e}")
    import traceback
    traceback.print_exc()
