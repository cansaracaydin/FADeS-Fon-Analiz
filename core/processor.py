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

        # 3. Sharpe Oranı (Risksiz getiri varsayımı: %30 alınabilir ama 0 alıyoruz basitlik için)
        mean_return = daily_returns.mean() * 252
        if volatility == 0 or np.isnan(volatility):
            sharpe = 0
        else:
            sharpe = mean_return / volatility

        # 4. Maximum Drawdown & Calmar Ratio
        rolling_max = df['Price'].cummax()
        drawdown = (df['Price'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Calmar: Yıllık Getiri / |Max Drawdown|
        if max_drawdown != 0:
            calmar = mean_return / abs(max_drawdown)
        else:
            calmar = 0

        # 5. Sortino Oranı (Negatif Volatilite)
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        if downside_std == 0 or np.isnan(downside_std):
            sortino = 0
        else:
            sortino = mean_return / downside_std

        return {
            "Toplam Getiri": total_return,
            "Yıllık Volatilite": volatility,
            "Sharpe Oranı": sharpe,
            "Sortino Oranı": sortino,
            "Calmar Oranı": calmar,
            "Max Drawdown": max_drawdown
        }

    def calculate_comparative_metrics(self, fund_df, benchmark_df):
        """
        Benchmark ile karşılaştırmalı metrikler: Beta, Alpha, Treynor, R-Square, Information Ratio
        """
        if fund_df.empty or benchmark_df.empty: return {}
        
        # Ensure Dates are datetime and naive
        f_df = fund_df.copy()
        b_df = benchmark_df.copy()
        
        f_df['Date'] = pd.to_datetime(f_df['Date'])
        if f_df['Date'].dt.tz is not None: f_df['Date'] = f_df['Date'].dt.tz_localize(None)
            
        b_df['Date'] = pd.to_datetime(b_df['Date'])
        if b_df['Date'].dt.tz is not None: b_df['Date'] = b_df['Date'].dt.tz_localize(None)
        
        # Merge on Date
        merged = pd.merge(f_df[['Date', 'Daily_Return']], b_df[['Date', 'Daily_Return']], on='Date', suffixes=('_f', '_b')).dropna()
        
        # Debugging / Lower threshold
        if len(merged) < 20: return {}
        
        Y = merged['Daily_Return_f']
        X = merged['Daily_Return_b']
        
        # Beta Calculation
        covariance = np.cov(Y, X)[0][1]
        variance = np.var(X)
        if variance == 0: return {}
        
        beta = covariance / variance
        
        # Alpha Calculation (Jensen's Alpha) - Risk Free assumed 0 for simplicity daily
        # Alpha = R_p - (Beta * R_m)
        mean_fund = Y.mean() * 252
        mean_bench = X.mean() * 252
        alpha = mean_fund - (beta * mean_bench)
        
        # R-Squared
        correlation_matrix = np.corrcoef(Y, X)
        correlation_xy = correlation_matrix[0,1]
        r_squared = correlation_xy**2
        
        # Treynor Ratio: (Rp - Rf) / Beta
        if abs(beta) > 0.01:
            treynor = mean_fund / beta
        else:
            treynor = 0
            
        # Information Ratio: (Rp - Rb) / TrackingError
        active_return = Y - X
        tracking_error = active_return.std() * np.sqrt(252)
        if tracking_error > 0:
            info_ratio = (mean_fund - mean_bench) / tracking_error
        else:
            info_ratio = 0
            
        return {
            "Beta": beta,
            "Alpha": alpha,
            "Treynor Oranı": treynor,
            "R-Kare (R²)": r_squared,
            "Information Ratio": info_ratio
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

    def normalize_for_comparison(self, df):
        if df.empty: return pd.DataFrame()
        
        df = df.copy()
        result_frames = []
        
        # Her fon için başlangıcı 0'a endeksle
        for fund in df['FundCode'].unique():
            sub = df[df['FundCode'] == fund].copy().sort_values("Date")
            if not sub.empty:
                start_price = sub.iloc[0]['Price']
                sub['Cumulative_Return'] = (sub['Price'] / start_price) - 1
                result_frames.append(sub)
                
        if result_frames:
            return pd.concat(result_frames, ignore_index=True)
        return df

    def calculate_drawdown_series(self, df):
        if df.empty: return pd.DataFrame()
        df = df.sort_values("Date").copy()
        
        rolling_max = df['Price'].cummax()
        df['Drawdown'] = (df['Price'] - rolling_max) / rolling_max
        return df[['Date', 'Drawdown']]
        
    def calculate_monthly_returns(self, df):
        if df.empty: return pd.DataFrame()
        
        df = df.copy()
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        
        monthly = df.groupby(['Year', 'Month'])['Price'].last().pct_change()
        
        # Pivot table (Yıl x Ay)
        pivot = monthly.reset_index().pivot(index='Year', columns='Month', values='Price')
        
        # Ay isimleri
        pivot.columns = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'][0:len(pivot.columns)]
        return pivot

    # ---------------------------------------------------------
    # SİMÜLASYON FONKSİYONU
    # ---------------------------------------------------------
    def calculate_portfolio_simulation(self, full_df, weights_dict, initial_capital=100000):
        if full_df.empty or not weights_dict: return pd.DataFrame()

        selected_funds = list(weights_dict.keys())
        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        
        # Pivot ve Temizlik
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
    # MARKOWITZ ETKİN SINIR (EFFICIENCY FRONTIER)
    # ---------------------------------------------------------
    def calculate_efficient_frontier(self, full_df, selected_funds, num_portfolios=2000):
        if full_df.empty or len(selected_funds) < 2:
            return pd.DataFrame(), {}

        df_filtered = full_df[full_df['FundCode'].isin(selected_funds)].copy()
        
        try:
            pivot_returns = df_filtered.pivot_table(index='Date', columns='FundCode', values='Daily_Return')
        except:
            return pd.DataFrame(), {}

        pivot_returns = pivot_returns.replace([np.inf, -np.inf], np.nan).dropna()
        if pivot_returns.empty: return pd.DataFrame(), {}

        mean_returns = pivot_returns.mean() * 252
        cov_matrix = pivot_returns.cov() * 252
        num_assets = len(pivot_returns.columns)

        # --- HELPER FUNCTIONS ---
        def get_ret_vol_sharpe(weights):
            weights = np.array(weights)
            ret = np.sum(mean_returns * weights)
            vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sr = ret / vol if vol > 0 else 0
            return np.array([ret, vol, sr])

        def neg_sharpe(weights):
            return -get_ret_vol_sharpe(weights)[2]

        def minimize_volatility(weights):
            return get_ret_vol_sharpe(weights)[1]

        # Constraints & Bounds
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        # MAX WEIGHT CONSTRAINTS (Diversification)
        # Her fon en az %2, en çok %60 olabilir.
        # Böylece %100 tek fona yığılmayı engelleriz.
        bounds = tuple((0.02, 0.60) for _ in range(num_assets))
        init_guess = [1./num_assets] * num_assets

        # 1. MAX SHARPE PORTFOLIO
        opt_sharpe = sco.minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        max_sharpe_w = opt_sharpe.x
        max_sharpe_metrics = get_ret_vol_sharpe(max_sharpe_w)
        
        best_sharpe = {
            'Return': max_sharpe_metrics[0],
            'Volatility': max_sharpe_metrics[1],
            'Sharpe': max_sharpe_metrics[2],
            'Weights': {col: round(w, 2) for col, w in zip(pivot_returns.columns, max_sharpe_w)}
        }

        # 2. MIN VOLATILITY PORTFOLIO
        opt_vol = sco.minimize(minimize_volatility, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        min_vol_w = opt_vol.x
        min_vol_metrics = get_ret_vol_sharpe(min_vol_w)
        
        min_vol = {
            'Return': min_vol_metrics[0],
            'Volatility': min_vol_metrics[1],
            'Sharpe': min_vol_metrics[2],
            'Weights': {col: round(w, 2) for col, w in zip(pivot_returns.columns, min_vol_w)}
        }

        # 3. EFFICIENT FRONTIER CURVE
        # Target returns range from Min Vol Return to Max Asset Return
        target_rets = np.linspace(min_vol_metrics[0], mean_returns.max(), 30)
        frontier_vol = []
        frontier_ret = []

        for tr in target_rets:
            cons = (
                {'type': 'eq', 'fun': lambda x: get_ret_vol_sharpe(x)[0] - tr},
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
            )
            res = sco.minimize(minimize_volatility, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
            if res.success:
                frontier_ret.append(tr)
                frontier_vol.append(res.fun)
        
        frontier_df = pd.DataFrame({'Volatility': frontier_vol, 'Return': frontier_ret})

        # 4. RANDOM SIMULATION (Background Cloud)
        sim_results = []
        for _ in range(num_portfolios):
            w = np.random.random(num_assets)
            w /= np.sum(w)
            sim_results.append(get_ret_vol_sharpe(w))
        
        sim_df = pd.DataFrame(sim_results, columns=['Return', 'Volatility', 'Sharpe'])

        return {
            'sim_df': sim_df,
            'frontier_df': frontier_df,
            'max_sharpe': best_sharpe,
            'min_vol': min_vol
        }

    # ---------------------------------------------------------
    # VAR (VALUE AT RISK)
    # ---------------------------------------------------------
    def calculate_value_at_risk(self, full_df, weights_dict, initial_capital=100000, confidence_level=0.95):
        sim_df = self.calculate_portfolio_simulation(full_df, weights_dict, initial_capital)
        if sim_df.empty: return None

        returns = sim_df['Daily_Return']
        mean = returns.mean()
        std = returns.std()

        z_score = 2.33 if confidence_level == 0.99 else 1.645
        var_pct = (z_score * std) - mean
        var_amt = initial_capital * var_pct

        return {"VaR_Amount": abs(var_amt), "VaR_Percent": var_pct, "Confidence": confidence_level}

    # ---------------------------------------------------------
    # MONTE CARLO SİMÜLASYONU
    # ---------------------------------------------------------
    def run_monte_carlo_simulation(self, full_df, weights_dict, initial_capital, days_forward=180, num_simulations=50):
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
        
        target_col = 'Oran' if 'Oran' in inf_copy.columns else 'Aylık Enflasyon'
        if target_col not in inf_copy.columns: return df

        merged = pd.merge(df, inf_copy[['YearMonth', target_col]], on='YearMonth', how='left')
        last_val = inf_copy[target_col].iloc[-1] if not inf_copy.empty else 3.0
        merged[target_col] = merged[target_col].fillna(last_val)
        
        merged['Daily_Inf_Factor'] = (1 + (merged[target_col]/100))**(1/30)
        merged['Cum_Inf_Index'] = merged['Daily_Inf_Factor'].cumprod()
        merged['Real_Return'] = ((1 + merged['Cumulative_Return']) / merged['Cum_Inf_Index']) - 1
        
        return merged