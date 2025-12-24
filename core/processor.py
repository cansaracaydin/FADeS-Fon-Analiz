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
        return df

    def calculate_risk_metrics(self, df):
        """
        ÖZET İSTATİSTİKLER (Tablo ve Scatter Grafik için)
        """
        if df.empty or len(df) < 2:
            return None

        # Günlük Getiri
        daily_returns = df['Daily_Return'].dropna() if 'Daily_Return' in df.columns else df['Price'].pct_change().dropna()
        
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
        Fon ve Benchmark (Dolar/Altın) kıyaslaması için normalize eder.
        """
        if df_fund.empty or df_benchmark.empty:
            return pd.DataFrame()

        merged = pd.merge(
            df_fund[["Date", "Price", "FundName"]],
            df_benchmark[["Date", "Price"]],
            on="Date",
            how="inner",
            suffixes=("", "_Bench")
        )

        if merged.empty: return pd.DataFrame()

        merged["Fund_Cumulative"] = (merged["Price"] / merged["Price"].iloc[0]) - 1
        merged[f"{benchmark_name}_Cumulative"] = (merged["Price_Bench"] / merged["Price_Bench"].iloc[0]) - 1

        return merged

    # ---------------------------------------------------------
    # SİMÜLASYON FONKSİYONU
    # ---------------------------------------------------------
    def calculate_portfolio_simulation(self, full_df, weights_dict, initial_capital=100000):
        """
        Birden fazla fonun ağırlıklı ortalamasını alarak SANAL PORTFÖY oluşturur.
        """
        if full_df.empty or not weights_dict:
            return pd.DataFrame()

        selected_funds = list(weights_dict.keys())
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        
        pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return').dropna()

        if pivot_returns.empty:
            return pd.DataFrame()

        ordered_weights = [weights_dict[code] for code in pivot_returns.columns]
        
        total_weight = sum(ordered_weights)
        if total_weight > 0:
            ordered_weights = [w / total_weight for w in ordered_weights]
        
        portfolio_daily_ret = pivot_returns.dot(ordered_weights)
        
        portfolio_df = pd.DataFrame(index=portfolio_daily_ret.index)
        portfolio_df['Daily_Return'] = portfolio_daily_ret
        portfolio_df['Cumulative_Return'] = (1 + portfolio_df['Daily_Return']).cumprod() - 1
        portfolio_df['Price'] = initial_capital * (1 + portfolio_df['Cumulative_Return'])
        
        portfolio_df = portfolio_df.reset_index()
        portfolio_df['FundCode'] = "PORTFOY"
        portfolio_df['FundName'] = "Simülasyon Portföyüm"
        
        return portfolio_df

    # ---------------------------------------------------------
    # MARKOWITZ ETKİN SINIR (OPTİMİZASYON)
    # ---------------------------------------------------------
    def calculate_efficient_frontier(self, full_df, selected_funds, num_portfolios=2000):
        if full_df.empty or len(selected_funds) < 2:
            return pd.DataFrame(), None

        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return').dropna()

        if pivot_returns.empty:
            return pd.DataFrame(), None

        mean_returns = pivot_returns.mean() * 252
        cov_matrix = pivot_returns.cov() * 252
        num_assets = len(selected_funds)

        results = []
        max_sharpe_ratio = -1
        optimal_weights = []

        for _ in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)

            portfolio_return = np.sum(mean_returns * weights)
            portfolio_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if portfolio_std_dev == 0:
                sharpe_ratio = 0
            else:
                sharpe_ratio = portfolio_return / portfolio_std_dev

            if sharpe_ratio > max_sharpe_ratio:
                max_sharpe_ratio = sharpe_ratio
                optimal_weights = weights

            results.append({
                'Return': portfolio_return,
                'Volatility': portfolio_std_dev,
                'Sharpe': sharpe_ratio
            })

        sim_df = pd.DataFrame(results)
        best_weights = {col: round(w, 2) for col, w in zip(pivot_returns.columns, optimal_weights)}
        best_portfolio_stats = {
            'Return': np.sum(mean_returns * optimal_weights),
            'Volatility': np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))),
            'Sharpe': max_sharpe_ratio,
            'Weights': best_weights
        }
        return sim_df, best_portfolio_stats

    # ---------------------------------------------------------
    # VAR (VALUE AT RISK) HESAPLAMA
    # ---------------------------------------------------------
    def calculate_value_at_risk(self, full_df, weights_dict, initial_capital=100000, confidence_level=0.95):
        if full_df.empty or not weights_dict:
            return None

        selected_funds = list(weights_dict.keys())
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return').dropna()

        if pivot_returns.empty: return None

        ordered_weights = np.array([weights_dict[code] for code in pivot_returns.columns])
        total_weight = sum(ordered_weights)
        if total_weight > 0:
            ordered_weights = ordered_weights / total_weight

        cov_matrix = pivot_returns.cov()
        avg_return = pivot_returns.mean()
        
        portfolio_mean = np.sum(avg_return * ordered_weights)
        portfolio_std = np.sqrt(np.dot(ordered_weights.T, np.dot(cov_matrix, ordered_weights)))

        if confidence_level == 0.95: z_score = 1.645
        elif confidence_level == 0.99: z_score = 2.33
        else: z_score = 1.645

        var_percent = (z_score * portfolio_std) - portfolio_mean
        var_amount = initial_capital * var_percent

        return {
            "VaR_Amount": var_amount,
            "VaR_Percent": var_percent,
            "Confidence": confidence_level
        }

    # ---------------------------------------------------------
    # YENİ ÖZELLİK 3: MONTE CARLO SİMÜLASYONU
    # ---------------------------------------------------------
    def run_monte_carlo_simulation(self, full_df, weights_dict, initial_capital, days_forward=180, num_simulations=50):
        """
        Geometrik Brownian Motion kullanarak geleceğe yönelik fiyat senaryoları üretir.
        """
        if full_df.empty or not weights_dict:
            return pd.DataFrame()

        # 1. Geçmiş Veriden Portföy İstatistiği Çıkar
        selected_funds = list(weights_dict.keys())
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return').dropna()

        if pivot_returns.empty: return pd.DataFrame()

        ordered_weights = np.array([weights_dict[code] for code in pivot_returns.columns])
        total_weight = sum(ordered_weights)
        if total_weight > 0:
            ordered_weights = ordered_weights / total_weight

        # Günlük Ortalama ve Varyans
        avg_daily_return = np.sum(pivot_returns.mean() * ordered_weights)
        daily_volatility = np.sqrt(np.dot(ordered_weights.T, np.dot(pivot_returns.cov(), ordered_weights)))
        
        # 2. Simülasyonu Başlat
        simulation_df = pd.DataFrame()
        
        # Gelecek tarihler
        last_date = df_filtered['Date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, days_forward + 1)]
        simulation_df['Date'] = future_dates

        # Her bir senaryo için döngü
        for sim in range(num_simulations):
            # Rastgele Şoklar (Normal Dağılım)
            random_shocks = np.random.normal(0, 1, days_forward)
            
            # Fiyat Yolu Formülü (Geometric Brownian Motion)
            # Price_t = Price_t-1 * exp((mu - 0.5 * sigma^2) + sigma * Z)
            
            simulated_returns = (avg_daily_return - 0.5 * daily_volatility**2) + (daily_volatility * random_shocks)
            
            price_path = [initial_capital]
            for r in simulated_returns:
                price_path.append(price_path[-1] * np.exp(r))
            
            # İlk gün (bugün) hariç geleceği al
            simulation_df[f'Senaryo {sim+1}'] = price_path[1:]

        return simulation_df