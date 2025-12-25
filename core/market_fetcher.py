# -*- coding: utf-8 -*-
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
            # Bitiş tarihini 1 gün ileri at (Yahoo Finance bazen son günü keser)
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            end_str = end_dt.strftime("%Y-%m-%d")

            # Veriyi indir
            df = yf.download(symbol, start=start_date, end=end_str, progress=False)
            
            if df.empty:
                return pd.DataFrame()

            # Veri setini temizle
            df = df.reset_index()
            
            # Sütun isimlerini düzelt (Yahoo bazen MultiIndex döndürür)
            if isinstance(df.columns, pd.MultiIndex):
                # Sadece ilk seviyeyi (Price, Open vb.) al
                df.columns = df.columns.get_level_values(0)
            
            # Sadece Tarih ve Kapanış Fiyatı lazım
            # 'Close' veya 'Adj Close' sütunu var mı kontrol et
            col_name = "Adj Close" if "Adj Close" in df.columns else "Close"
            
            if col_name not in df.columns:
                 return pd.DataFrame() # İstenen sütun yoksa boş dön

            df = df[["Date", col_name]].copy()
            df = df.rename(columns={col_name: "Price"})
            
            # Tarih formatını standartlaştır
            df["Date"] = pd.to_datetime(df["Date"])
            
            # Hafta sonlarını doldur (Fonlarla eşleşmesi için)
            df = df.set_index("Date").resample("D").ffill().reset_index()

            return df

        except Exception as e:
            print(f"Piyasa verisi hatası ({symbol}): {e}")
            return pd.DataFrame()