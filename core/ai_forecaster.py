# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    XGBRegressor = None  # Will use GradientBoosting as fallback
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures
from datetime import timedelta

class AIForecaster:
    def __init__(self):
        pass

    def calculate_technical_indicators(self, df):
        """
        Gelişmiş Teknik İndikatörler (Faz 2: Expanded)
        """
        data = df.copy()
        
        # === MOVING AVERAGES (Multiple Timeframes) ===
        data['SMA_5'] = data['Price'].rolling(window=5).mean()
        data['SMA_10'] = data['Price'].rolling(window=10).mean()
        data['SMA_20'] = data['Price'].rolling(window=20).mean()
        data['SMA_50'] = data['Price'].rolling(window=50).mean()
        
        # Exponential Moving Averages
        data['EMA_12'] = data['Price'].ewm(span=12, adjust=False).mean()
        data['EMA_26'] = data['Price'].ewm(span=26, adjust=False).mean()
        
        # === MOMENTUM INDICATORS ===
        # Price Rate of Change
        data['ROC_5'] = ((data['Price'] - data['Price'].shift(5)) / data['Price'].shift(5)) * 100
        data['ROC_10'] = ((data['Price'] - data['Price'].shift(10)) / data['Price'].shift(10)) * 100
        
        # Momentum (raw price difference)
        data['Momentum_5'] = data['Price'] - data['Price'].shift(5)
        data['Momentum_10'] = data['Price'] - data['Price'].shift(10)
        
        # === RSI ===
        delta = data['Price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # === BOLLINGER BANDS ===
        sma20 = data['Price'].rolling(window=20).mean()
        std20 = data['Price'].rolling(window=20).std()
        data['BB_Upper'] = sma20 + (2 * std20)
        data['BB_Lower'] = sma20 - (2 * std20)
        data['BB_Percent'] = (data['Price'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])
        
        # === MACD ===
        ema12 = data['Price'].ewm(span=12, adjust=False).mean()
        ema26 = data['Price'].ewm(span=26, adjust=False).mean()
        data['MACD'] = ema12 - ema26
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
        
        # === VOLATILITY ===
        data['Volatility_7d'] = data['Price'].rolling(window=7).std()
        data['Volatility_14d'] = data['Price'].rolling(window=14).std()
        data['Volatility_ATR_Proxy'] = data['Price'].rolling(window=14).std()

        return data

    def prepare_features(self, df, lags=7):  # Optimized to 7 (not 10)
        if df.empty or 'Price' not in df.columns:
            return pd.DataFrame()
            
        data = df[['Date', 'Price']].copy()
        data = data.sort_values('Date')
        
        # --- 1. LOG RETURN (Daha Normal Dağılım İçin) ---
        data['Return'] = np.log(data['Price'] / data['Price'].shift(1))
        
        data = self.calculate_technical_indicators(data)
        
        # --- 2. Selective Lags (Quality over Quantity) ---
        # Only lag the most predictive features
        core_features = ['Return', 'RSI', 'MACD', 'MACD_Histogram', 'Volatility_7d']
        
        for col in core_features:
            if col not in data.columns:
                continue
            for i in range(1, lags + 1):
                if col == 'Return':
                    # All return lags (most important)
                    data[f'Return_Lag{i}'] = data['Return'].shift(i)
                elif i <= 2:  # Only first 2 lags for indicators
                    data[f'{col}_Lag{i}'] = data[col].shift(i)

        data = data.dropna()
        return data

    def train_and_predict(self, df, days_forward=30):
        if df.empty or len(df) < 90: return None, 0

        # Feature Prep (Optimized to 7)
        lags = 7
        model_data = self.prepare_features(df, lags=lags)
        if model_data.empty: return None, 0

        # Focused feature set (Quality > Quantity)
        features = [f'Return_Lag{i}' for i in range(1, lags + 1)] + \
                   ['RSI_Lag1', 'RSI_Lag2',
                    'MACD_Lag1', 'MACD_Lag2',
                    'MACD_Histogram_Lag1',
                    'Volatility_7d_Lag1', 'Volatility_7d_Lag2']
        
        # Filter features that exist
        features = [f for f in features if f in model_data.columns]
        
        X = model_data[features]
        y = model_data['Return']

        # Train-Test Split (Increased to 20% test)
        split = int(len(X) * 0.8)
        X_train, y_train = X.iloc[:split], y.iloc[:split]
        X_test, y_test = X.iloc[split:], y.iloc[split:]
        
        if len(X_train) < 10: return None, 0

        # --- OUTLIER REMOVAL (More Conservative: 5σ) ---
        # Extreme outliers only (black swan events)
        mean_y = y_train.mean()
        std_y = y_train.std()
        # 5 standard deviations (keep more data)
        mask = (np.abs(y_train - mean_y) <= 5 * std_y)
        X_train = X_train[mask]
        y_train = y_train[mask]

        # --- REMOVED POLYNOMIAL FEATURES ---
        # Polynomial features were causing severe overfitting
        # Using raw features instead
        
        # Scaling (Keep this - important for GradientBoosting)
        scaler_X = MinMaxScaler()
        X_train_scaled = scaler_X.fit_transform(X_train)
        X_test_scaled = scaler_X.transform(X_test)
        
        # --- MODEL SELECTION (XGBoost or GradientBoosting) ---
        if XGBOOST_AVAILABLE:
            # XGBoost with regularization
            param_dist = {
                'n_estimators': [100, 200, 300],
                'learning_rate': [0.01, 0.03, 0.05],
                'max_depth': [3, 4, 5],
                'subsample': [0.7, 0.8],
                'colsample_bytree': [0.7, 0.8],
                'min_child_weight': [3, 5, 7],
                'reg_alpha': [0.01, 0.1, 1],
                'reg_lambda': [1, 2, 3]
            }
            model = XGBRegressor(random_state=42, tree_method='hist')
        else:
            # Fallback to GradientBoosting
            param_dist = {
                'n_estimators': [100, 200, 300],
                'learning_rate': [0.01, 0.03, 0.05],
                'max_depth': [3, 4, 5],
                'subsample': [0.7, 0.8],
                'min_samples_leaf': [3, 5, 7]
            }
            model = GradientBoostingRegressor(random_state=42)
        
        random_search = RandomizedSearchCV(model, param_distributions=param_dist, n_iter=15, cv=3, n_jobs=-1, random_state=42)
        
        if len(X_train) > 1000:
            sample_X = X_train_scaled[-1000:]
            sample_y = y_train[-1000:]
            random_search.fit(sample_X, sample_y)
        else:
            random_search.fit(X_train_scaled, y_train)
            
        best_model = random_search.best_estimator_
        
        # --- TIME SERIES CROSS-VALIDATION ---
        # Get more reliable score using proper time series validation
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=3)
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(X_train_scaled):
            X_tr, X_val = X_train_scaled[train_idx], X_train_scaled[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            
            temp_model = random_search.best_estimator_
            temp_model.fit(X_tr, y_tr)
            cv_scores.append(temp_model.score(X_val, y_val))
        
        print(f"CV Scores: {cv_scores}")
        print(f"Mean CV R²: {np.mean(cv_scores):.3f}")
        
        # Final training on all training data
        best_model.fit(X_train_scaled, y_train)
        
        # Test score
        r2_score = best_model.score(X_test_scaled, y_test)
        
        preds_test = best_model.predict(X_test_scaled)
        std_error = (y_test - preds_test).std()

        # RECURSIVE FORECAST
        future_predictions = []
        sim_df = df.iloc[-150:].copy() 
        current_price = df['Price'].iloc[-1]
        
        cum_std = 0
        
        for i in range(days_forward):
            current_feats_df = self.prepare_features(sim_df, lags=lags)
            if current_feats_df.empty: break
                
            last_row_vals = current_feats_df.iloc[-1][features].values.reshape(1, -1)
            # Apply Scaler -> Predict (NO POLY anymore)
            last_row_scaled = scaler_X.transform(last_row_vals)
            
            # Predict Log Return
            pred_log_return = best_model.predict(last_row_scaled)[0]
            
            # Convert back to Price: P_new = P_old * exp(log_ret)
            # Log Return dönüşümü: exp(r) - 1 değil, direkt exp(r) çarpımıdır.
            # ln(P_t/P_{t-1}) = r  => P_t = P_{t-1} * e^r
            new_price = current_price * np.exp(pred_log_return)
            
            new_date = df['Date'].max() + timedelta(days=i+1)
            
            cum_std += std_error
            # Log return hatasını fiyata yansıtmak yaklaşık olarak:
            # P_up = P * exp(r + 1.96*sigma)
            lower_bound = new_price * np.exp(-1.96 * cum_std)
            upper_bound = new_price * np.exp(1.96 * cum_std)

            future_predictions.append({
                'Date': new_date,
                'Predicted_Price': new_price,
                'Lower_Bound': lower_bound,
                'Upper_Bound': upper_bound
            })
            
            new_row = pd.DataFrame({'Date': [new_date], 'Price': [new_price]})
            sim_df = pd.concat([sim_df, new_row], ignore_index=True)
            current_price = new_price 
            
        return pd.DataFrame(future_predictions), r2_score
