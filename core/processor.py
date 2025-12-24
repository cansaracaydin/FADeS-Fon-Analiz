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
        
        # Hareketli ortalama ilk 30 günü NaN yapar.
        df.dropna(inplace=True)
        return df

    def calculate_risk_metrics(self, df):
        """
        ÖZET İSTATİSTİKLER (Tablo ve Scatter Grafik için)
        """
        if df.empty or len(df) < 2:
            return None

        # Günlük Getiri
        daily_returns = df['Price'].pct_change().dropna()
        
        # 1. Toplam Getiri (%)
        total_return = ((df['Price'].iloc[-1] - df['Price'].iloc[0]) / df['Price'].iloc[0])

        # 2. Yıllık Volatilite (Risk)
        volatility = daily_returns.std() * np.sqrt(252)

        # 3. Sharpe Oranı
        mean_return = daily_returns.mean() * 252
        if volatility == 0:
            sharpe = 0
        else:
            sharpe = mean_return / volatility

        # 4. Maximum Drawdown
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
        """
        if df.empty: return {}

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
        
        # 1. Geçmiş Dönem Getirileri
        for name, days in periods.items():
            target_date = latest_date - timedelta(days=days)
            past_data = df[df["Date"] <= target_date]
            
            if not past_data.empty:
                past_price = past_data.iloc[-1]["Price"]
                if past_price > 0:
                    ret = (latest_price - past_price) / past_price
                    results[name] = ret
                else:
                    results[name] = None
            else:
                results[name] = None

        # 2. Yılbaşından Bugüne (YTD)
        current_year = latest_date.year
        ytd_data = df[df["Date"].dt.year < current_year]
        
        if not ytd_data.empty:
            ytd_price = ytd_data.iloc[-1]["Price"]
            results["YTD (Yılbaşı)"] = (latest_price - ytd_price) / ytd_price
        else:
            results["YTD (Yılbaşı)"] = None

        return results

    def calculate_correlation_matrix(self, full_df):
        """
        Korelasyon Matrisi Hesaplar
        """
        if full_df.empty: return pd.DataFrame()

        pivot_df = full_df.pivot_table(index="Date", columns="FundCode", values="Price")
        returns_df = pivot_df.pct_change().dropna()
        corr_matrix = returns_df.corr()
        
        return corr_matrix

    def normalize_for_comparison(self, df_fund, df_benchmark, benchmark_name="USD/TRY"):
        """
        YENİ EKLENEN FONKSİYON: 
        Fon ve Benchmark (Dolar/Altın) verilerini tarihe göre eşleştirip,
        ikisini de aynı noktadan (0%) başlatarak kıyaslama tablosu oluşturur.
        
        """
        if df_fund.empty or df_benchmark.empty:
            return pd.DataFrame()

        # 1. Tarihleri eşleştir (Inner Join: İkisinde de olan tarihleri al)
        merged = pd.merge(
            df_fund[["Date", "Price", "FundName"]],
            df_benchmark[["Date", "Price"]],
            on="Date",
            how="inner",
            suffixes=("", "_Bench")
        )

        if merged.empty: return pd.DataFrame()

        # 2. İkisini de 0 noktasından başlat (Rebase)
        # Formül: (Fiyat / İlk_Gün_Fiyatı) - 1
        # Böylece grafik 0'dan başlar ve kimin daha çok kazandırdığı net görünür.
        merged["Fund_Cumulative"] = (merged["Price"] / merged["Price"].iloc[0]) - 1
        merged[f"{benchmark_name}_Cumulative"] = (merged["Price_Bench"] / merged["Price_Bench"].iloc[0]) - 1

        return merged