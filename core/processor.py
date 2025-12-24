import pandas as pd
import numpy as np
from datetime import timedelta

class DataProcessor:
    def __init__(self):
        pass

    def clean_data(self, df):
        if df.empty: return df

        keep_cols = ['Date', 'Price', 'FundCode', 'FundName']
        existing_cols = [c for c in keep_cols if c in df.columns]
        df = df[existing_cols].copy()

        # 1. TARİH DÜZELTME
        if 'Date' in df.columns:
            try:
                # Önce numeric mi diye bak (timestamp)
                df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
                df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            except:
                # Değilse string parse dene
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)

        # 2. FİYAT DÜZELTME
        if 'Price' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['Price']):
                df['Price'] = df['Price'].astype(str).str.replace('.', '', regex=False)
                df['Price'] = df['Price'].str.replace(',', '.', regex=False)
                df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

        df = df.dropna(subset=['Date', 'Price'])
        df = df.sort_values('Date').reset_index(drop=True)

        return df

    def add_financial_metrics(self, df):
        """Zaman serisi metrikleri (Grafik için)"""
        if df.empty or 'Price' not in df.columns: return df
        
        df = df.copy()
        df['Daily_Return'] = df['Price'].pct_change()
        df['Cumulative_Return'] = (1 + df['Daily_Return']).cumprod() - 1
        df['MA_30'] = df['Price'].rolling(window=30).mean()
        
        # Hareketli ortalama ilk 30 günü NaN yapar, grafikte boşluk olmaması için silebiliriz
        # Ancak dönem analizi için veri kaybetmemek adına dropna'yı kapatıyorum veya dikkatli kullanıyorum.
        # Senin orijinal kodunda dropna vardı, onu koruyorum ama veri azsa dikkat.
        df.dropna(inplace=True)
        return df

    def calculate_risk_metrics(self, df):
        """
        ÖZET İSTATİSTİKLER (Tablo ve Scatter Grafik için)
        Tek bir satır (Scalar) değerler döndürür.
        """
        if df.empty or len(df) < 2:
            return None

        # Günlük Getiri
        daily_returns = df['Price'].pct_change().dropna()
        
        # 1. Toplam Getiri (%)
        total_return = ((df['Price'].iloc[-1] - df['Price'].iloc[0]) / df['Price'].iloc[0])

        # 2. Yıllık Volatilite (Risk)
        # Standart sapma * kök(252 iş günü)
        volatility = daily_returns.std() * np.sqrt(252)

        # 3. Sharpe Oranı (Risksiz faiz 0 varsayıldı)
        # (Yıllık Getiri / Yıllık Risk)
        mean_return = daily_returns.mean() * 252
        if volatility == 0:
            sharpe = 0
        else:
            sharpe = mean_return / volatility

        # 4. Maximum Drawdown (En büyük düşüş)
        rolling_max = df['Price'].cummax()
        drawdown = (df['Price'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        return {
            "Toplam Getiri": total_return,
            "Yıllık Volatilite (Risk)": volatility,
            "Sharpe Oranı": sharpe,
            "Max Drawdown (En Büyük Kayıp)": max_drawdown
        }

    def calculate_period_returns(self, df):
        """
        TEFAS Tarzı Dönemsel Getiriler (1 Ay, 3 Ay, 6 Ay, Yılbaşı)
        Bu fonksiyon son eklediğimiz özelliktir.
        """
        if df.empty: return {}

        # Tarihe göre sırala (Emin olmak için)
        df = df.sort_values("Date")
        latest_date = df.iloc[-1]["Date"]
        latest_price = df.iloc[-1]["Price"]
        
        periods = {
            "1 Ay": 30,
            "3 Ay": 90,
            "6 Ay": 180,
            "1 Yıl": 365
        }
        
        results = {}
        
        # 1. Geçmiş Dönem Getirileri (1 Ay, 3 Ay vb.)
        for name, days in periods.items():
            target_date = latest_date - timedelta(days=days)
            # Hedef tarihe eşit veya önceki en son veriyi bul
            past_data = df[df["Date"] <= target_date]
            
            if not past_data.empty:
                past_price = past_data.iloc[-1]["Price"]
                if past_price > 0:
                    ret = (latest_price - past_price) / past_price
                    results[name] = ret
                else:
                    results[name] = None
            else:
                results[name] = None # Veri yetmiyor

        # 2. Yılbaşından Bugüne (YTD - Year to Date)
        current_year = latest_date.year
        # Geçen yılın son işlem gününü bulmaya çalışıyoruz
        ytd_data = df[df["Date"].dt.year < current_year]
        
        if not ytd_data.empty:
            ytd_price = ytd_data.iloc[-1]["Price"] # Geçen yılın son fiyatı
            results["YTD (Yılbaşı)"] = (latest_price - ytd_price) / ytd_price
        else:
            # Eğer geçen yılın verisi yoksa (fon yeni kurulduysa veya veri seti kısaysa)
            # Veri setindeki ilk günü baz alabiliriz veya boş geçebiliriz.
            # Şimdilik veri yoksa boş geçelim.
            results["YTD (Yılbaşı)"] = None

        return results