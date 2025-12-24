import yfinance as yf
import pandas as pd

class MarketFetcher:
    def __init__(self):
        pass

    def fetch_benchmark(self, symbol, start_date, end_date):
        """
        Yahoo Finance üzerinden Dolar (USDTRY=X) veya Altın (GC=F) verisi çeker.
        """
        try:
            # Yahoo Finance bazen son günü eksik getirir, o yüzden end_date'i 1 gün ileri atıyoruz
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            end_str = end_dt.strftime("%Y-%m-%d")

            # Veriyi indir
            df = yf.download(symbol, start=start_date, end=end_str, progress=False)
            
            if df.empty:
                return pd.DataFrame()

            # Veri setini temizle
            df = df.reset_index()
            
            # Sadece Tarih ve Kapanış Fiyatı lazım
            # yfinance sütunları bazen MultiIndex gelir, onu düzeltelim:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df[["Date", "Close"]].copy()
            df = df.rename(columns={"Close": "Price"})
            
            # Tarih formatını standartlaştır
            df["Date"] = pd.to_datetime(df["Date"])
            
            # Hafta sonlarını (Cumartesi-Pazar) doldurmak için (Fonlarla eşleşsin diye)
            # Forward Fill (Önceki günün fiyatını kopyala) yöntemi
            df = df.set_index("Date").resample("D").ffill().reset_index()

            return df

        except Exception as e:
            print(f"Piyasa verisi hatası ({symbol}): {e}")
            return pd.DataFrame()