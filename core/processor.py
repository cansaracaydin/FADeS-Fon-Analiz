# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import scipy.optimize as sco
from datetime import datetime, timedelta
import warnings

# Gereksiz tarih formatı uyarılarını sustur
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

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
                if pd.api.types.is_numeric_dtype(df['Date']):
                    df['Date'] = pd.to_datetime(df['Date'], unit='ms')
                else:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
            except:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

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
        df = df.sort_values("Date")
        
        # Günlük Getiri
        df['Daily_Return'] = df['Price'].pct_change()
        
        # --- FIX: Sonsuz ve NaN değerleri temizle ---
        df['Daily_Return'] = df['Daily_Return'].replace([np.inf, -np.inf], np.nan)
        df['Daily_Return'] = df['Daily_Return'].fillna(0)

        # Kümülatif Getiri
        df['Cumulative_Return'] = (1 + df['Daily_Return']).cumprod() - 1
        df['MA_30'] = df['Price'].rolling(window=30).mean()
        
        return df

    def calculate_risk_metrics(self, df):
        """
        ÖZET İSTATİSTİKLER (Tablo ve Scatter Grafik için)
        """
        if df.empty or len(df) < 2:
            return None

        # Daily_Return yoksa hesapla ve temizle
        if 'Daily_Return' in df.columns:
            daily_returns = df['Daily_Return'].replace([np.inf, -np.inf], np.nan).fillna(0)
        else:
            daily_returns = df['Price'].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # 1. Toplam Getiri (%)
        try:
            total_return = ((df['Price'].iloc[-1] - df['Price'].iloc[0]) / df['Price'].iloc[0])
        except:
            total_return = 0

        # 2. Yıllık Volatilite (Risk)
        volatility = daily_returns.std() * np.sqrt(252)

        # 3. Sharpe Oranı
        mean_return = daily_returns.mean() * 252
        if volatility == 0 or np.isnan(volatility):
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
        if df.empty: return {}

        df = df.sort_values("Date")
        latest_date = df.iloc[-1]["Date"]
        latest_price = df.iloc[-1]["Price"]
        
        periods = {"1 Ay": 30, "3 Ay": 90, "6 Ay": 180, "1 Yıl": 365}
        results = {}
        
        for name, days in periods.items():
            target_date = latest_date - timedelta(days=days)
            past_data = df[df["Date"] <= target_date]
            
            if not past_data.empty:
                past_price = past_data.iloc[-1]["Price"]
                if past_price > 0:
                    ret = (latest_price - past_price) / past_price
                    results[name] = ret
                else: results[name] = None
            else: results[name] = None

        current_year = latest_date.year
        ytd_data = df[df["Date"].dt.year < current_year]
        if not ytd_data.empty:
            ytd_price = ytd_data.iloc[-1]["Price"]
            results["YTD (Yılbaşı)"] = (latest_price - ytd_price) / ytd_price
        else: results["YTD (Yılbaşı)"] = None

        return results

    def calculate_correlation_matrix(self, full_df):
        if full_df.empty: return pd.DataFrame()
        pivot_df = full_df.pivot_table(index="Date", columns="FundCode", values="Price")
        returns_df = pivot_df.pct_change().dropna()
        return returns_df.corr()

    def normalize_for_comparison(self, df_fund, df_benchmark, benchmark_name="USD/TRY"):
        if df_fund.empty or df_benchmark.empty: return pd.DataFrame()

        merged = pd.merge(
            df_fund[["Date", "Price", "FundName"]],
            df_benchmark[["Date", "Price"]],
            on="Date", how="inner", suffixes=("", "_Bench")
        )
        if merged.empty: return pd.DataFrame()

        merged["Fund_Cumulative"] = (merged["Price"] / merged["Price"].iloc[0]) - 1
        merged[f"{benchmark_name}_Cumulative"] = (merged["Price_Bench"] / merged["Price_Bench"].iloc[0]) - 1
        return merged

    # ---------------------------------------------------------
    # SİMÜLASYON FONKSİYONU
    # ---------------------------------------------------------
    def calculate_portfolio_simulation(self, full_df, weights_dict, initial_capital=100000):
        if full_df.empty or not weights_dict: return pd.DataFrame()

        selected_funds = list(weights_dict.keys())
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        
        # Pivot ve Temizlik (inf temizliği eklendi)
        pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return')
        pivot_returns = pivot_returns.replace([np.inf, -np.inf], np.nan).dropna()

        if pivot_returns.empty: return pd.DataFrame()

        ordered_weights = []
        for code in pivot_returns.columns:
            ordered_weights.append(weights_dict.get(code, 0))
        
        total_weight = sum(ordered_weights)
        if total_weight > 0:
            ordered_weights = [w / total_weight for w in ordered_weights]
        else: return pd.DataFrame()

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
    # MARKOWITZ ETKİN SINIR (DÜZELTİLMİŞ - HATA VERMEZ)
    # ---------------------------------------------------------
    def calculate_efficient_frontier(self, full_df, selected_funds, num_portfolios=2000):
        if full_df.empty or len(selected_funds) < 2:
            return pd.DataFrame(), {}

        # Veri Hazırlama
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        
        try:
            pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return')
        except:
            return pd.DataFrame(), {}

        # --- Temizlik: Sonsuzları ve NaN'ları uçur ---
        pivot_returns = pivot_returns.replace([np.inf, -np.inf], np.nan).dropna()

        if pivot_returns.empty:
            return pd.DataFrame(), {}

        mean_returns = pivot_returns.mean() * 252
        cov_matrix = pivot_returns.cov() * 252
        num_assets = len(pivot_returns.columns)

        # --- FIX: Varsayılan değerler (Crash Koruması) ---
        # Eğer optimizasyon başarısız olursa boş liste dönmesin diye Eşit Ağırlık atıyoruz.
        optimal_weights = np.ones(num_assets) / num_assets 
        max_sharpe_ratio = -1e9 # Çok düşük başlatıyoruz

        results = []

        # 1. Simülasyon (Rastgele)
        for _ in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)

            portfolio_return = np.sum(mean_returns * weights)
            portfolio_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if portfolio_std_dev == 0: sharpe_ratio = 0
            else: sharpe_ratio = portfolio_return / portfolio_std_dev

            results.append({
                'Return': portfolio_return,
                'Volatility': portfolio_std_dev,
                'Sharpe': sharpe_ratio
            })

        # 2. Scipy Optimizasyonu (Matematiksel)
        def neg_sharpe(weights):
            p_ret = np.sum(mean_returns * weights)
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -p_ret / p_vol if p_vol > 0 else 0

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1. / num_assets,]

        try:
            opt_result = sco.minimize(neg_sharpe, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)
            if opt_result.success:
                optimal_weights = opt_result.x
                # İyileştirilmiş Sharpe
                p_ret = np.sum(mean_returns * optimal_weights)
                p_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
                max_sharpe_ratio = p_ret / p_vol if p_vol > 0 else 0
        except:
            pass # Hata olursa varsayılan (eşit ağırlık) kalır

        sim_df = pd.DataFrame(results)
        
        # Sonuçları paketle (optimal_weights artık asla boş değil)
        best_weights = {col: round(w, 2) for col, w in zip(pivot_returns.columns, optimal_weights)}
        
        best_portfolio_stats = {
            'Return': np.sum(mean_returns * optimal_weights),
            'Volatility': np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))),
            'Sharpe': max_sharpe_ratio,
            'Weights': best_weights
        }
        
        return sim_df, best_portfolio_stats

    # ---------------------------------------------------------
    # VAR (VALUE AT RISK)
    # ---------------------------------------------------------
    def calculate_value_at_risk(self, full_df, weights_dict, initial_capital=100000, confidence_level=0.95):
        if full_df.empty or not weights_dict: return None

        sim_df = self.calculate_portfolio_simulation(full_df, weights_dict, initial_capital)
        if sim_df.empty: return None

        returns = sim_df['Daily_Return']
        mean = returns.mean()
        std = returns.std()

        if confidence_level == 0.95: z_score = 1.645
        elif confidence_level == 0.99: z_score = 2.33
        else: z_score = 1.645

        var_percent = (z_score * std) - mean
        var_amount = initial_capital * var_percent

        return {
            "VaR_Amount": abs(var_amount),
            "VaR_Percent": var_percent,
            "Confidence": confidence_level
        }

    # ---------------------------------------------------------
    # MONTE CARLO SİMÜLASYONU
    # ---------------------------------------------------------
    def run_monte_carlo_simulation(self, full_df, weights_dict, initial_capital, days_forward=180, num_simulations=50):
        if full_df.empty or not weights_dict: return pd.DataFrame()

        sim_df = self.calculate_portfolio_simulation(full_df, weights_dict, initial_capital)
        if sim_df.empty: return pd.DataFrame()

        returns = sim_df['Daily_Return']
        mu = returns.mean()
        sigma = returns.std()
        
        last_date = sim_df['Date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, days_forward + 1)]
        
        results = pd.DataFrame({'Date': future_dates})
        
        for i in range(num_simulations):
            shocks = np.random.normal(0, 1, days_forward)
            sim_returns = (mu - 0.5 * sigma**2) + (sigma * shocks)
            
            price_path = [initial_capital]
            for r in sim_returns:
                price_path.append(price_path[-1] * np.exp(r))
            
            results[f'Sim_{i}'] = price_path[1:]
            
        return results

    # ---------------------------------------------------------
    # REEL GETİRİ (ENFLASYONLU)
    # ---------------------------------------------------------
    def calculate_real_returns(self, df, inflation_df):
        if df.empty or 'Cumulative_Return' not in df.columns: return df
        if inflation_df is None or inflation_df.empty: return df 
        
        df = df.copy()
        df['YearMonth'] = df['Date'].dt.to_period('M')
        
        inf_copy = inflation_df.copy()
        if 'Tarih' in inf_copy.columns:
            inf_copy['Date'] = pd.to_datetime(inf_copy['Tarih'])
        inf_copy['YearMonth'] = inf_copy['Date'].dt.to_period('M')
        
        # Sütun adı kontrolü
        target_col = 'Oran' if 'Oran' in inf_copy.columns else 'Aylık Enflasyon'
        if target_col not in inf_copy.columns: return df

        merged = pd.merge(df, inf_copy[['YearMonth', target_col]], on='YearMonth', how='left')
        
        # Eksikleri doldur
        last_val = inf_copy[target_col].iloc[-1] if not inf_copy.empty else 3.0
        merged[target_col] = merged[target_col].fillna(last_val)
        
        merged['Daily_Inf_Factor'] = (1 + (merged[target_col]/100))**(1/30)
        merged['Cum_Inf_Index'] = merged['Daily_Inf_Factor'].cumprod()
        merged['Real_Return'] = ((1 + merged['Cumulative_Return']) / merged['Cum_Inf_Index']) - 1
        
        return merged