
import yfinance as yf
import datetime

print("--- TESTING SIMPLE YFINANCE ---")
try:
    ticker = "THYAO.IS"
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date.today()
    
    print(f"Downloading {ticker}...")
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    if not df.empty:
        print("✅ SUCCESS!")
        print(df.head())
        print(df.tail())
    else:
        print("❌ EMPTY DATAFRAME returned.")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
