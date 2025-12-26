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
            if df["Date"].dt.tz is not None:
                df["Date"] = df["Date"].dt.tz_localize(None)
            
            # Fiyatın sayısal olduğundan emin ol
            df["Price"] = pd.to_numeric(df["Price"], errors='coerce')
            df = df.dropna(subset=["Price"])

            # Hafta sonlarını doldur (Fonlarla eşleşmesi için)
            df = df.set_index("Date").resample("D").ffill().reset_index()

            return df

        except Exception as e:
            print(f"Piyasa verisi hatası ({symbol}): {e}")
            return pd.DataFrame()

    def fetch_live_data(self):
        """
        Anlık piyasa verilerini (BIST, Dolar, Euro, Altın) çeker.
        Hata toleransı için son 5 günü tarar ve en son mevcut veriyi alır.
        """
        # USDTRY=X genellikle TRY=X'ten daha stabildir.
        symbols = ['XU100.IS', 'USDTRY=X', 'EURTRY=X', 'GC=F']
        rename_map = {'USDTRY=X': 'TRY=X'} # Code uses TRY=X internal key
        
        try:
            # 5 günlük veri çek
            df = yf.download(symbols, period='5d', progress=False)
            
            if df.empty: return {}

            # MultiIndex Handling
            if isinstance(df.columns, pd.MultiIndex):
                # 'Close' veya 'Adj Close' katmanını al
                if 'Close' in df.columns.levels[0]:
                    df_close = df['Close']
                elif 'Adj Close' in df.columns.levels[0]:
                    df_close = df['Adj Close']
                else:
                    # Fallback: ilk level neyse onu al
                    df_close = df.xs(df.columns.levels[0][0], axis=1, level=0)
            else:
                df_close = df

            # Rename columns if needed (USDTRY=X -> TRY=X)
            df_close = df_close.rename(columns=rename_map)
            
            # Helper to get last valid value
            def get_last_valid(ticker):
                if ticker in df_close.columns:
                    series = df_close[ticker].dropna()
                    if not series.empty:
                        return series.iloc[-1]
                return 0

            bist = get_last_valid('XU100.IS')
            usd = get_last_valid('TRY=X') # After rename
            eur = get_last_valid('EURTRY=X')
            ons = get_last_valid('GC=F')
            
            # Eğer USD hala 0 ise TRY=X sembolüyle tekrar dene (Fallback)
            if usd == 0:
                try:
                    alt_usd = yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1]
                    usd = alt_usd
                except:
                    pass

            # Gram Altın Hesabı: (Ons * Dolar) / 31.1035
            gram = (ons * usd) / 31.1035 if ons and usd else 0
            
            return {
                "BIST 100": bist,
                "Dolar/TL": usd,
                "Euro/TL": eur,
                "Gram Altın": gram
            }
        except Exception as e:
            print(f"Canlı veri hatası: {e}")
            return {}

    def fetch_market_history(self, period="1y"):
        """
        Piyasa analizi için geçmiş verileri çeker (Grafikler için).
        """
        symbols = ['XU100.IS', 'TRY=X', 'EURTRY=X', 'GC=F']
        try:
            # Download history
            df = yf.download(symbols, period=period, progress=False)
            
            # Handle MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                try:
                    df = df['Close']
                except KeyError:
                    df = df['Adj Close']
            
            # Forward Fill (Tatil günlerini doldur)
            df = df.ffill().dropna()

            # Calculate Gram Gold History
            # Gram = (Ons * USD) / 31.1035
            if 'GC=F' in df.columns and 'TRY=X' in df.columns:
                df['Gram Altın'] = (df['GC=F'] * df['TRY=X']) / 31.1035
            
            # Rename for display
            rename_map = {
                'XU100.IS': 'BIST 100',
                'TRY=X': 'Dolar/TL',
                'EURTRY=X': 'Euro/TL'
            }
            df = df.rename(columns=rename_map)
            
            return df
        except Exception as e:
            print(f"Geçmiş veri hatası: {e}")
            return pd.DataFrame()