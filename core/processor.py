import pandas as pd
import numpy as np

class DataProcessor:
    def __init__(self):
        pass

    def clean_data(self, df):
        if df.empty:
            return df

        keep_cols = ['Date', 'Price', 'FundCode', 'FundName']
        existing_cols = [c for c in keep_cols if c in df.columns]
        df = df[existing_cols].copy()

        # --- DEBUG: Verinin ham halini görelim ---
        try:
            ornek_tarih = df['Date'].iloc[0]
            ornek_fiyat = df['Price'].iloc[0]
            print(f"   🔎 [DEBUG] Gelen Veri -> Tarih: {ornek_tarih} (Tip: {type(ornek_tarih)}) | Fiyat: {ornek_fiyat} (Tip: {type(ornek_fiyat)})")
        except:
            pass
        # -----------------------------------------

        # 1. TARİH DÜZELTME
        if 'Date' in df.columns:
            # Unix Timestamp (Milisaniye) gelirse
            # Örn: 1695427200000 (int) veya "1695427200000" (str)
            try:
                # Önce sayıya çevirmeyi dene
                df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
                # Sayı olanları datetime yap (unit='ms' milisaniye demek)
                df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            except:
                # Olmazsa klasik string tarih dene (Gün.Ay.Yıl)
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)

        # 2. FİYAT DÜZELTME
        if 'Price' in df.columns:
            # Eğer zaten sayıysa (float/int) ve NaN değilse dokunma
            if pd.api.types.is_numeric_dtype(df['Price']):
                pass
            else:
                # String ise temizlik yap
                df['Price'] = df['Price'].astype(str)
                # "3.450,20" formatı gelirse:
                # 1. Noktaları sil -> "3450,20"
                # 2. Virgülü noktaya çevir -> "3450.20"
                df['Price'] = df['Price'].str.replace('.', '', regex=False)
                df['Price'] = df['Price'].str.replace(',', '.', regex=False)
                df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

        # 3. Sıralama ve Temizleme
        df = df.dropna(subset=['Date', 'Price']) # Dönüşemeyenleri at
        df = df.sort_values('Date').reset_index(drop=True)

        return df

    def add_financial_metrics(self, df):
        if df.empty or 'Price' not in df.columns:
            print("   ⚠️ Veri boş veya fiyat sütunu yok.")
            return df
        
        # Fiyat ve Tarih boşsa sil
        df = df.dropna(subset=['Price', 'Date'])
        
        if df.empty:
            print("   ⚠️ Temizlik sonrası veri kalmadı.")
            return df

        # Getiri Hesaplamaları
        df['Daily_Return'] = df['Price'].pct_change()
        df['Cumulative_Return'] = (1 + df['Daily_Return']).cumprod() - 1
        df['MA_30'] = df['Price'].rolling(window=30).mean()
        
        # İlk satır NaN olacağı için temizle
        df.dropna(inplace=True)

        return df